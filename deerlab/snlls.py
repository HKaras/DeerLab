import numpy as np
import math as m
from scipy.optimize import least_squares, lsq_linear
from numpy.linalg import solve
from cvxopt import matrix, solvers
import copy

# Import DeerLab depencies
import deerlab as dl
from deerlab.utils import jacobianest, goodness_of_fit, hccm
from deerlab.nnls import cvxnnls, fnnls, nnlsbpp

def snlls(y,Amodel,par0,lb=[],ub=[],lbl=[],ubl=[],nnlsSolver='cvx', penalty=None, weights=1,
          regtype='tikhonov', regparam='aic', multiStarts = 1, regOrder=2, alphaOptThreshold=1e-3,
          nonLinTolFun=1e-9, nonLinMaxIter=1e8, linTolFun=1e-15, linMaxIter=1e4, huberparam = 1.35,
          uqanalysis = True):
    """
    Separable Non-linear Least Squares Solver
    =========================================
    
    Fits a linear set of parameters (x) and non-linear parameters (p)
    by solving the following non-linear least squares problem:
 
            [x,p] = argmin || A(p)*x - y||^2
                     s.t.   x in [lbl,ubl]
                            p in [lb,ub]
 
    When solving the linear problem: argmin_x ||y - A*x||^2  the solver will
    identify and adapt automatically to the following scenarios:
        - Well-conditioned + unconstrained       x = solve(A,y);
        - Well-conditioned + constrained         x = lsqlin(A,y,lb,ub)
        - Ill-conditioned  + unconstrained       x = solve(AtA + alpha^2*LtL, Kty)
        - Ill-conditioned  + constrained         x = lsqlin(AtA + alpha^2*LtL,Kty,lb,ub)
        - Ill-conditioned  + non-negativity      x = fnnls((AtA + alpha^2*LtL),Kty)
    By default, for poorly conditioned cases, Tikhonov regularization with
    automatic AIC-based regularization parameter selection is used.
   
    Arguments:
    ----------
    y (N-element array or list of arrays)
        Input data to be fitted.
    Amodel (callable)
        Function taking an array of non-linear parameters and 
        returning a NxM-element matrix or a list of matrices.
    par0 (W-element array)
        Start values of the non-linear parameters.
    lb (W-element array)       
        Lower bounds for the non-linear parameters.
    ub (W-element array)      
        Upper bounds for the non-linear parameters.
    lbl (M-element array)       
        Lower bounds for the linear parameters.
    ubl (M-element array)       
        Upper bounds for the linear parameters.
 
    Return:
    -------
    pnlin (W-element array)
        Fitted non-linear parameters
    nlin (M-element array)
        Fitted linear parameters
    paramuq (obj)
        Uncertainty quantification of the joined parameter
        set (linear + non-linear parameters). The confidence intervals
        of the individual subsets can be requested via:
                paramuq.ci(n)           - n%-CI of the full parameter set
                paramuq.ci(n,'lin')     - n%-CI of the linear parameter set
                paramuq.ci(n,'nonlin')  - n%-CI of the non-linear parameter set
    stats (dict)
        Goodness of fit statistical estimators
 
    Additional keyword arguments:
    -----------------------------
    penalty (boolean)
        Forces the use of a regularization penalty on the solution of the linear problem.
        If not specified it is determined automatically based con the condition number of the non-linear model ``Amodel``.
    regType (str) 
        Regularization penalty type ('tikh','tv','huber')
    regOrder (scalar,int)
        Order of the regularization operator
    regParam (str or scalar) 
        Regularization parameter selection method ('lr','lc','cv','gcv',
        'rgcv','srgcv','aic','bic','aicc','rm','ee','ncp','gml','mcl')
        or value of the regularization parameter. By default 'aic' is used.
    alphaOptThreshold (scalar) 
        Relative parameter change threshold for reoptimizing the regularization parameter
        when using a selection method (default: 1e-3).
    nnlsSolver (str)
        Solver used to solve a non-negative least-squares problem: 'fnnls', 'nnlsbpp', or 'cvx' (default).
    weights (array) 
        Array of weighting coefficients for the individual signals in global fitting.
    multiStarts (scalar)
        Number of starting points for global optimization.
    nonLinMaxIter (scalar) 
        Non-linear solver maximal number of iterations.
    nonLinTolFun (scalar)   
        Non-linear solver function tolerance.
    linMaxIter (scalar)     
        Linear solver maximal number of iterations.
    linTolFun (scalar)      
        Linear solver function tolerance.
    uqanalysis (boolean)
        Enable/disable the uncertainty quantification analysis.
    """
    # Ensure that all arrays are numpy.nparray
    par0,lb,ub,lbl,ubl = [np.atleast_1d(var) for var in (par0,lb,ub,lbl,ubl)]
    
    # Parse multiple datsets and non-linear operators into a single concatenated vector/matrix
    y, Amodel, weights, subsets = dl.utils.parse_multidatasets(y, Amodel, weights)

    # Get info on the problem parameters and non-linear operator
    A0 = Amodel(par0)
    Nnonlin = len(par0)
    Nlin = np.shape(A0)[1]
    linfit = np.zeros(Nlin)
  
    # Determine whether to use regularization penalty
    illConditioned = np.linalg.cond(A0)>10
    if illConditioned and penalty is None:
        includePenalty = True
    else: 
        includePenalty = penalty

    # Checks for bounds constraints
    # ----------------------------------------------------------
    if not lb.size:
        lb = np.full(Nnonlin, -np.inf)

    if not ub.size:
        ub = np.full(Nnonlin, np.inf)

    if not lbl.size:
        lbl = np.full(Nlin, -np.inf)

    if not ubl.size:
        ubl = np.full(Nlin, np.inf)
    
    # Check that the correct number of boundaries are given
    if len(lb) != Nnonlin or len(ub) != Nnonlin:
        raise TypeError('The lower/upper bounds of the non-linear problem must have ',Nnonlin,' elements')
    if len(lbl) != Nlin or len(ubl) != Nlin:
        raise TypeError('The lower/upper bounds of the linear problem must have ',Nlin,' elements')
    
    # Check that the boundaries are valid
    if np.any(ub<lb) or np.any(ubl<lbl):
        raise ValueError('The upper bounds cannot be larger than the lower bounds.')
    # Check that the non-linear start values are inside the box constraint
    if np.any(par0>ub) or np.any(par0<lb):
        raise ValueError('The start values are outside of the specified bounds.')
    # ----------------------------------------------------------


    # Check if the nonlinear and linear problems are constrained
    nonLinearConstrained = (not np.all(np.isinf(lb))) or (not np.all(np.isinf(ub)))
    linearConstrained = (not np.all(np.isinf(lbl))) or (not np.all(np.isinf(ubl)))
    # Check for non-negativity constraints on the linear solution
    nonNegativeOnly = (np.all(lbl==0)) and (np.all(np.isinf(ubl)))


    if includePenalty:
        # Use an arbitrary axis
        ax = np.arange(1,Nlin+1)
        # Get regularization operator
        regOrder = np.minimum(Nlin-1,regOrder)
        L = dl.regoperator(ax,regOrder)
    else:
        L = np.eye(Nlin,Nlin)

    # Prepare the linear solver
    # ----------------------------------------------------------
    if not linearConstrained:
        # Unconstrained linear LSQ
        linSolver = lambda AtA,Aty: solve(AtA,Aty)
        parseResult = lambda result: result

    elif linearConstrained and not nonNegativeOnly:
        # Constrained linear LSQ
        linSolver = lambda AtA,Aty: lsq_linear(AtA, Aty, bounds=(lbl,ubl), method='bvls')
        parseResult = lambda result: result.x

    elif linearConstrained and nonNegativeOnly:
        # Non-negative linear LSQ
        if nnlsSolver is 'fnnls':
            linSolver = lambda AtA,Aty: fnnls(AtA, Aty,tol = linTolFun)
        elif nnlsSolver is 'nnlsbpp':
            linSolver = lambda AtA,Aty: nnlsbpp(AtA, Aty,np.linalg.solve(AtA,Aty))
        elif nnlsSolver is 'cvx':
            linSolver = lambda AtA,Aty: cvxnnls(AtA, Aty, tol = linTolFun)
        parseResult = lambda result: result
    # ----------------------------------------------------------
    
    # Containers for alpha-update checks
    check = False
    regparam_prev = 0
    par_prev = [0]*len(par0)

    def ResidualsFcn(p):
    #===========================================================================
        """ 
        Residuals function
        ------------------
        Provides vector of residuals, which is the objective function for the non-linear least-squares solver. 
        """
        
        nonlocal par_prev, check, regparam_prev, linfit
        # Non-linear model evaluation
        A = Amodel(p)
        
        # Regularization components
        if includePenalty:
            if type(regparam) is str:
                # If the parameter vector has not changed by much...
                if check and all(abs(par_prev-p)/p < alphaOptThreshold):
                    # ...use the alpha optimized in the previous iteration
                    alpha = regparam_prev
                else:
                    # ...otherwise optimize with current settings
                    alpha = dl.selregparam(y,A,ax,regtype,regparam, regorder=regOrder)
                    check = True
            else:
                # Fixed regularization parameter
                alpha =  regparam
            
            # Store current iteration data for next one
            par_prev = p
            regparam_prev = alpha
            
        else:
            # Non-linear operator without penalty
            alpha = 0

        # Components for linear least-squares        
        AtA,Aty = dl.lsqcomponents(y,A,L,alpha,weights,regtype=regtype)

        # Solve the linear least-squares problem
        result = linSolver(AtA,Aty)
        linfit = parseResult(result)
        linfit = np.atleast_1d(linfit)
        # Evaluate full model residual
        yfit = A@linfit
        # Compute residual vector
        res = yfit - y
        if includePenalty:
            penalty = alpha*L@linfit
            # Augmented residual
            res = np.concatenate((res, penalty))
            res,_ = _augment(res,[],regtype,alpha,L,linfit,huberparam,Nnonlin)

        return res
    #===========================================================================


    # Preprare multiple start global optimization if requested
    if multiStarts>1 and not nonLinearConstrained:
        raise TypeError('Multistart optimization cannot be used with unconstrained non-linear parameters.')
    multiStartPar0 = dl.utils.multistarts(multiStarts,par0,lb,ub)

    # Pre-allocate containers for multi-start run
    fvals,nonlinfits,linfits = ( [] for _ in range(3))

    # Multi-start global optimization
    for par0 in multiStartPar0:
        # Run the non-linear solver
        sol = least_squares(ResidualsFcn ,par0, bounds=(lb,ub), max_nfev=int(nonLinMaxIter), ftol=nonLinTolFun)
        nonlinfits.append(sol.x)
        linfits.append(linfit) 
        fvals.append(sol.cost)
    # Find global minimum from multiple runs
    globmin = np.argmin(fvals)
    linfit = linfits[globmin]
    nonlinfit = nonlinfits[globmin]
    Afit = Amodel(nonlinfit)
    yfit =  Afit@linfit

    # Uncertainty analysis
    #--------------------------------------------------------
    if uqanalysis:
        # Compue the residual vector
        res = weights*(yfit - y)

        # Compute the Jacobian for the linear and non-linear parameters
        fcn = lambda p: Amodel(p)@linfit
        Jnonlin,_ = jacobianest(fcn,nonlinfit)
        Jlin = Afit
        J = np.concatenate((Jnonlin, Jlin),1)

        # Augment the residual and Jacobian with the regularization penalty on the linear parameters
        res,J = _augment(res,J,regtype,regparam_prev,L,linfit,huberparam,Nnonlin)

        # Calculate the heteroscedasticity consistent covariance matrix 
        covmatrix = hccm(J,res,'HC1')
        
        # Get combined parameter sets and boundaries
        parfit = np.concatenate((nonlinfit, linfit))
        lbs = np.concatenate((lb, lbl))
        ubs = np.concatenate((ub, ubl))

        # Construct the uncertainty quantification object
        paramuq_ = dl.uqst('covariance',parfit,covmatrix,lbs,ubs)
        paramuq = copy.deepcopy(paramuq_)

        def ci(coverage,type='full'):
        #===========================================================================
            "Wrapper around the CI function handle of the uncertainty structure"
            # Get requested confidence interval of joined parameter set
            paramci = paramuq_.ci(coverage)
            if type == 'nonlin':
                    # Return only confidence intervals on non-linear parameters
                    paramci = paramci[range(Nnonlin),:]
            elif type == 'lin':
                    # Return only confidence intervals on linear parameters
                    paramci = paramci[Nnonlin:,:]
            return paramci
        #===========================================================================

        # Add the function to the confidence interval function call
        paramuq.ci = ci
    else:
        paramuq = []
    # Goodness-of-fit
    # --------------------------------------
    stats = []
    for subset in subsets: 
        Ndof = len(y[subset]) - Nnonlin
        stats.append(goodness_of_fit(y[subset],yfit[subset],Ndof))
    if len(stats)==1: 
        stats = stats[0]

    return nonlinfit, linfit, paramuq, stats
# ===========================================================================================


def _augment(res,J,regtype,alpha,L,x,eta,Nnonlin):
# ===========================================================================================
    """ 
    LSQ residual and Jacobian augmentation
    =======================================

    Augments the residual and the Jacobian of a LSQ problem to include the
    regularization penalty. The residual and Jacobian contributions of the 
    specific regularization methods are analytically introduced. 
    """
    eps = np.finfo(float).eps
    # Compute the regularization penalty augmentation for the residual and the Jacobian
    if regtype is 'tikhonov':
        resreg = L@x
        Jreg = L
    elif regtype is 'tv':
        resreg =((L@x)**2 + eps)**(1/4)
        Jreg = 2/4*((( ( (L@x)**2 + eps)**(-3/4) )*(L@x))[:, np.newaxis]*L)
    elif regtype is 'huber':
        resreg = np.sqrt(np.sqrt((L@x/eta)**2 + 1) - 1)
        Jreg = 0.5/(eta**2)*( (((np.sqrt((L@x/eta)**2 + 1) - 1 + eps)**(-1/2)*(((L@x/eta)**2 + 1+ eps)**(-1/2)))*(L@x))[:, np.newaxis]*L )

    # Include regularization parameter
    resreg = alpha*resreg
    Jreg = alpha*Jreg

    # Augment jacobian and residual
    res = np.concatenate((res,resreg))
    if np.size(J) != 0:
        Jreg = np.concatenate((np.zeros((np.shape(L)[0],Nnonlin)), Jreg),1)
        J = np.concatenate((J,Jreg))

    return res,J
# ===========================================================================================