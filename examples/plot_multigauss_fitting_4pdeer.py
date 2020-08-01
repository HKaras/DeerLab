# %% [markdown]
"""
Multi-Gauss fit of a 4-pulse DEER signal
========================================

This example showcases how to fit a simple 4-pulse DEER signal with
background using a multi-Gauss model, i.e automatically optimizing the
number of Gaussians in the model.
"""
import numpy as np
import matplotlib.pyplot as plt
from deerlab import *


# %% [markdown]
# Model function for a 4pDEER dipolar kernel 
# ------------------------------------------
# The first step for this analysis requires the definition of a parametric dipolar kernel 
# for the description of a 4-pulse DEER experiment. 

def K4pdeer(par,t,r):

    # Unpack parameters
    lam,conc = par
    # Simualte background
    B = bg_hom3d(t,conc,lam)
    # Generate dipolar kernel
    K = dipolarkernel(t,r,lam,B)

    return K

# %% [markdown]
# Generating a dataset
# ---------------------

# %%
t = np.linspace(-0.25,4,300) # time axis, us
r = np.linspace(2.5,4.5,300) # distance axis, nm
param0 = [3, 0.3, 0.2, 3.5, 0.3, 0.45, 3.9, 0.2, 0.20] # parameters for three-Gaussian model
P = dd_gauss3(r,param0) # ground truth distance distribution
lam = 0.3 # modulation depth
conc = 250 # spin concentration, uM
noiselvl = 0.005 # noise level

# Generate 4pDEER dipolar signal with noise
np.random.seed(0)
V = K4pdeer([lam,conc],t,r)@P + whitegaussnoise(t,noiselvl)

# %% [markdown]
# Multi-Gauss fitting
# -------------------

# Parameter bounds:
#     lambda conc   rmean fwhm 
lb = [1,  0.05] # distribution basis function lower bounds
ub = [20, 5] # distribution basis function upper bounds
lbK = [0, 0.05] # kernel parameters lower bounds
ubK = [1, 1500] # kernel parameters upper bounds

# Prepare the kernel model
Kmodel = lambda par: K4pdeer(par,t,r)
NGauss = 5 # maximum number of Gaussians

# Fit the kernel parameters with an optimized multi-Gauss distribution
Pfit,param,Puq,paramuq, metrics, Peval, stats = fitmultimodel(V,Kmodel,r,dd_gauss,NGauss,'aic',lb,ub,lbK,ubK)

# Extract the parameters
Kparfit = param[0]

# Get the time-domain fit
K = Kmodel(param[0])
Vfit = K@Pfit

# Confidence intervals of the fitted distance distribution
Pci95 = Puq.ci(95) # 95#-confidence interval
Pci50 = Puq.ci(50) # 50#-confidence interval

# %% [markdown]
# Akaike weights
#-----------------------------------------------------------------------------
# When comparing different parametric models is always a good idea to look
# at the Akaike weights for each model. They basically tell you the
# probability of a model being the most optimal choice.

# Compute the Akaike weights
dAIC = metrics - min(metrics)
Akaikeweights = 100*np.exp(-dAIC/2)/sum(np.exp(-dAIC/2))
# %%
# Plots

plt.figure(figsize=(10,5))

plt.subplot(3,2,1)
plt.plot(t,V,'k.')
plt.plot(t,Vfit,'b',linewidth=1.5)
plt.plot(t,(1-Kparfit[0])*bg_hom3d(t,Kparfit[1],Kparfit[0]),'b--',linewidth=1.5)
plt.tight_layout()
plt.grid(alpha=0.3)
plt.legend(['data','Vfit','Bfit'])
plt.xlabel('t [$\mu s$]')
plt.ylabel('V(t)')

plt.subplot(322)
plt.plot(r,P,'k',linewidth=1.5)
plt.plot(r,Pfit,'b',linewidth=1.5)
plt.fill_between(r,Pci50[:,0],Pci50[:,1],color='b',linestyle='None',alpha=0.45)
plt.fill_between(r,Pci95[:,0],Pci95[:,1],color='b',linestyle='None',alpha=0.25)
plt.tight_layout()
plt.grid(alpha=0.3)
plt.legend(['truth','optimal fit','95%-CI'])
plt.xlabel('r [nm]')
plt.ylabel('P(r)')

plt.subplot(323)
plt.bar(np.arange(NGauss)+1,metrics + abs(min(metrics)),facecolor='b',alpha=0.6)
plt.tight_layout()
plt.grid(alpha=0.3)
plt.ylabel('$\Delta AIC$')
plt.xlabel('Number of Gaussians')

plt.subplot(325)
plt.bar(np.arange(NGauss)+1,Akaikeweights,facecolor='b',alpha=0.6)
plt.tight_layout()
plt.grid(alpha=0.3)
plt.ylabel('Akaike Weight [%]')
plt.xlabel('Number of Gaussians')

plt.subplot(3,2,(4,6))
for i in range(len(Peval)):
    plt.plot(r,P + 2*i,'k',r,Peval[i] + 2*i,'b-',linewidth=1.5)
plt.tight_layout()
plt.grid(alpha=0.3)
plt.xlabel('r [nm]')
plt.ylabel('Number of Gaussians')
plt.legend(['truth','fit'])
