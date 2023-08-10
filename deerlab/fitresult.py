import numpy as np
from deerlab.dd_models import dd_gauss
import inspect 
import matplotlib.pyplot as plt
import difflib



class FitResult(dict):
# ========================================================================
    r""" Represents the results of either the :ref:`fit` or :ref:`snlls` functions. 
    Depending on which function is used, the attributes and methods of the FitResult will be different.

 
    Attributes
    ----------
    model : ndarray
        The fitted model response.
    modelUncert : 
        Uncertainty quantification of the fitted model response.
    regparam : float scalar
        Regularization parameter used in the fit.
    noiselvl: ndarray
        Estimated noise level of the data or user-provided noise level.
    success : bool
        Whether or not the optimizer exited successfully.
    cost : float
        Value of the cost function at the solution.
    residuals : ndarray
        Vector of residuals at the solution.
    stats : dict
        Goodness of fit statistical estimators:

        * ``stats['chi2red']`` - Reduced \chi^2 test
        * ``stats['r2']`` - R^2 test
        * ``stats['rmsd']`` - Root-mean squared deviation (RMSD)
        * ``stats['aic']`` - Akaike information criterion
        * ``stats['aicc']`` - Corrected Akaike information criterion
        * ``stats['bic']`` - Bayesian information criterion

    Methods
    -------
    plot(axis=None,xlabel='',gof=False)
        Function to display the results. It will display the fitted data. A 
        vector for the x-axis and its label can be specified by calling 
        FitResult.plot(axis=x,xlabel='xlabel'). A set of goodness-of-fit plots 
        can be displayed by enabling the gof option by calling FitResult.plot(gof=True).
    
    """

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            errstr = f"The results object has no attribute '{attr}'."
            attributes = [key for key in self.keys()]
            proposal = difflib.get_close_matches(attr, attributes)
            if len(proposal)>0:
                errstr += f' \n Did you mean: {proposal} ?'
            raise AttributeError(errstr)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __str__(self): 
        return self._summary

    def __repr__(self):
        if self.keys():
            m = max(map(len, list(self.keys()))) + 1
            return '\n'.join([k.rjust(m) + ': ' + repr(v)
                              for k, v in sorted(self.items())])
        else:
            return self.__class__.__name__ + "()"

    def __dir__(self):
        return list(self.keys())
    

    def _extarct_params_from_model(self, model):
        if callable(model):
            try:
                modelparam = model._parameter_list('vector')
            except AttributeError:
                modelparam = inspect.getfullargspec(model).args

        if not hasattr(self,'param'):
            raise ValueError('The fit object does not contain any fitted parameters.')

        # Enforce model normalization
        normalization = False
        normfactor_keys = []
        for key in model._parameter_list():
            param = getattr(model,key)
            if np.all(param.linear):
                if param.normalization is not None:
                    normfactor_key = f'{key}_scale'
                    normfactor_keys.append(normfactor_key)
                    model.addnonlinear(normfactor_key,lb=-np.inf,ub=np.inf,par0=1,description=f'Normalization factor of {key}')
                    getattr(model,normfactor_key).freeze(1)
                    normalization = True
                    

        # Get some basic information on the parameter vector
        modelparam = model._parameter_list(order='vector')
        param_idx = [[] for _ in model._parameter_list('vector')]
        idxprev = 0
        for islinear in [False,True]:
            for n,param in enumerate(model._parameter_list('vector')):
                if np.all(getattr(model,param).linear == islinear):
                    N = len(np.atleast_1d(getattr(model,param).idx))
                    param_idx[n] = np.arange(idxprev,idxprev + N)
                    idxprev += N  

        params = {key : fitvalue if len(fitvalue)>1 else fitvalue[0] for key,fitvalue in zip(modelparam,[self.param[idx] for idx in param_idx])}
        # Check that all parameters are in the fit object
        for param in modelparam:
            if not param in params: 
                raise KeyError(f'The fit object does not contain the {param} parameter.')

        return modelparam, params, param_idx

    def evaluate(self, model, *constants):
    # ----------------------------------------------------------------------------
        """
        Evaluate a model at the fitted parameter values. 

        Takes a model object or callable function model to be evaluated. All the 
        parameters in the model or in the callable definition must match their 
        corresponding parameter names in the FitResult object. Any model 
        constants present required by the model must be specified as a second 
        argument constants. It returns the model's response at the fitted 
        parameter values as an ndarray.

        Parameters
        ----------

        model : :ref:`Model` or callable
            Model object or callable function to be evaluated. All the parameters in the model or in the callable definition
            must match their corresponding parameter names in the ``FitResult`` object.   
        constants : array_like 
            Any model constants present required by the model.  
        
        Returns
        -------

        response : array_like 
            Model response at the fitted parameter values. 
        """

        modelparam, params, _ = self._extarct_params_from_model(model)
        parameters = {param: params[param] for param in modelparam}

        # Evaluate the input model
        response = model(*constants,**parameters)
        return response
    
    def propagate(self, model, *constants, lb=None, ub=None):
        """
        Propagate the uncertainty in the fit results to a model's response.

        Takes a model object or callable function model to be 
        evaluated. All the parameters in the model or in the callable definition 
        must match their corresponding parameter names in the FitResult object.
        Any model constants present required by the model must be specified as 
        a second argument constants. The lower bounds lb and upper bounds ub of
        the model's response can be specified as a third and fourth argument 
        respectively. It returns the model's response uncertainty 
        quantification as a UQResult object.
        Parameters
        ----------

        model : :ref:`Model` or callable
            Model object or callable function to be evaluated. All the parameters in the model or in the callable definition
            must match their corresponding parameter names in the ``FitResult`` object.   
        constants : array_like 
            Model constants. 
        lb : array_like, optional 
            Lower bounds of the model response.
        ub : array_like, optional 
            Upper bounds of the model response.   

        Returns
        -------

        responseUncert : :ref:`UQResult`
            Uncertainty quantification of the model's response.
        """

        modelparam,_, param_idx = self._extarct_params_from_model(model)
        # Determine the indices of the subset of parameters the model depends on
        subset = [param_idx[np.where(np.asarray(modelparam)==param)[0][0]] for param in modelparam]
        # Propagate the uncertainty from that subset to the model
        modeluq = self.paramUncert.propagate(lambda param: model(*constants,*[param[s] for s in subset]),lb,ub)
        return modeluq
    

    def plot(self,axis=None,xlabel=None,gof=False,fontsize=13):
            """
            Plot method for the FitResult object
            ====================================

            Plots the input dataset(s), their fits, and uncertainty bands.
            """
            yfits=self.model
            yuqs=self.modelUncert
            ys = self.y
            # Check which datasets are complex-valued
            complexy = [np.iscomplex(y).any() for y in ys]

            # Determine the distribution of the subplots in the figure
            nrows = len(ys) + np.sum(complexy)
            if gof:
                ncols = 4
                fig,axs = plt.subplots(nrows,ncols,figsize=[4*ncols,4*nrows], constrained_layout=True)
            else: 
                ncols = 1
                fig,axs = plt.subplots(nrows,ncols,figsize=[7*ncols,4*nrows])
            axs = np.atleast_1d(axs)
            axs = axs.flatten() 
            n = 0 # Index for subplots

            # If abscissa of the datasets are not specified, resort to default 
            if axis is None: 
                axis = [np.arange(len(y)) for y in ys]
            if not isinstance(axis,list): 
                axis = [axis]
            axis = [np.real(ax) for ax in axis]
            if xlabel is None: 
                xlabel = 'Array elements'

            # Go through every dataset
            for i,(y,yfit,yuq,noiselvl) in enumerate(zip(ys,yfits,yuqs,self.noiselvls)): 

                # If dataset is complex-valued, plot the real and imaginary parts separately
                if complexy[i]:
                    components = [np.real,np.imag]
                    componentstrs = [' (real)',' (imag)']
                else:
                    components = [np.real]
                    componentstrs = ['']
                for component,componentstr in zip(components,componentstrs):

                    # Plot the experimental signal and fit
                    axs[n].plot(axis[i],component(y),'.',color='grey',label='Data'+componentstr)
                    axs[n].plot(axis[i],component(yfit),color='#4550e6',label='Model fit')
                    if yuq.type!='void': 
                        axs[i].fill_between(axis[i],component(yuq.ci(95)[:,0]),component(yuq.ci(95)[:,1]),alpha=0.4,linewidth=0,color='#4550e6',label='95%-confidence interval')
                    axs[n].set_xlabel(xlabel,size=fontsize)
                    axs[n].set_ylabel(f'Dataset #{i+1}'+componentstr,size=fontsize)
                    axs[n].spines.right.set_visible(False)
                    axs[n].spines.top.set_visible(False) 
                    axs[n].legend(loc='best',frameon=False)
                    plt.autoscale(enable=True, axis='both', tight=True)
                    n += 1

                    # Plot the visual guides to assess the goodness-of-fit (if requested)
                    if gof: 
                        # Get the residual
                        residuals = component(yfit - y)

                        # Plot the residual values along the estimated noise level and mean value
                        axs[n].plot(axis[i],residuals,'.',color='grey')
                        axs[n].hlines(np.mean(residuals),axis[i][0],axis[i][-1],color='#4550e6',label='Mean')
                        axs[n].hlines(np.mean(residuals)+noiselvl,axis[i][0],axis[i][-1],color='#4550e6',linestyle='dashed',label='Estimated noise level')
                        axs[n].hlines(np.mean(residuals)-noiselvl,axis[i][0],axis[i][-1],color='#4550e6',linestyle='dashed')
                        axs[n].set_xlabel(xlabel,size=fontsize)        
                        axs[n].set_ylabel(f'Residual #{i+1}'+componentstr,size=fontsize)      
                        axs[n].spines.right.set_visible(False)
                        axs[n].spines.top.set_visible(False) 
                        axs[n].legend(loc='best',frameon=False)
                        plt.axis("tight")
                        n += 1

                        # Plot the histogram of the residuals weighted by the noise level, compared to the standard normal distribution
                        bins = np.linspace(-4,4,20)
                        axs[n].hist(residuals/noiselvl,bins,density=True,color='b',alpha=0.6, label='Residuals')
                        bins = np.linspace(-4,4,300)
                        N0 = dd_gauss(bins,0,1)
                        axs[n].get_yaxis().set_visible(False)
                        axs[n].fill(bins,N0,'k',alpha=0.4, label='$\mathcal{N}(0,1)$')
                        axs[n].set_xlabel('Normalized residuals',size=fontsize)       
                        axs[n].set_yticks([])
                        axs[n].spines.right.set_visible(False)
                        axs[n].spines.left.set_visible(False)
                        axs[n].spines.top.set_visible(False) 
                        axs[n].legend(loc='best',frameon=False)
                        n += 1

                        # Plot the autocorrelogram of the residuals, along the confidence region for a white noise vector
                        maxLag = len(residuals)-1
                        axs[n].acorr(residuals, usevlines=True, normed=True, maxlags=maxLag, lw=2,color='#4550e6',label='Residual autocorrelation')
                        threshold = 1.96/np.sqrt(len(residuals))
                        axs[n].fill_between(np.linspace(0,maxLag),-threshold,threshold,color='k',alpha=0.3,linewidth=0,label='White noise confidence region')
                        axs[n].get_yaxis().set_visible(False)
                        plt.axis("tight")
                        axs[n].set_xbound(lower=-0.5, upper=maxLag)
                        axs[n].spines.right.set_visible(False)
                        axs[n].spines.left.set_visible(False)
                        axs[n].spines.top.set_visible(False)
                        axs[n].set_xlabel('Lags',size=fontsize)       
                        axs[n].legend(loc='best',frameon=False)
                        n += 1

            # Adjust fontsize
            for ax in axs:
                for label in (ax.get_xticklabels() + ax.get_yticklabels()):
                    label.set_fontsize(fontsize)

            return fig
# ===========================================================================================
