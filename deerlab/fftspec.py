
# fftspec.py - Fast-Fourier transform spectrum
# ---------------------------------------------------------------
# This file is a part of DeerLab. License is MIT (see LICENSE.md). 
# Copyright(c) 2019-2020: Luis Fabregas, Stefan Stoll and other contributors.

import numpy as np
from numpy.fft import fft, fftshift, fftfreq

def fftspec(V,t,mode='abs',zerofilling='auto',apodization=True):
    """
    Fast-Fourier transform spectrum
 
    Parameters
    ----------
    V : array_like
        Signal to be processed.
    t : array_like
        Time axis, in microseconds.

    Returns
    -------
    nu : ndarray
        Frequency axis, in megahertz
    spec : ndarray
        FFT spectrum.

    Other parameters
    ----------------
    mode : string 
        Type of spectrum to be returned ('real','imag','abs'), the default is 'abs'.
    zerofilling : scalar
        Number of elements in the output FFT spectrum, the default is ``2*len(V)``.
    aposization : boolean
        Use of a Hamming apodization window, the default is True.
    """
    
    if zerofilling is 'auto':
        zerofilling = 2*len(V)

    #If requested apply Hamming apodization window
    if apodization:
        arg = np.linspace(0,np.pi,len(V))
        ApoWindow = 0.54 + 0.46*np.cos(arg)
        V = V*ApoWindow

    #Compute fft spectrum
    spec = fftshift(fft(V,zerofilling))

    #Get the requested component/type of spectrum
    if mode is 'abs':
            spec = np.abs(spec)
    elif mode is 'real':
            spec  = spec.real
    elif mode is 'imag':
            spec = spec.imag
    else:
        raise KeyError("Invalid spectrum mode. Must be 'abs', 'real', or 'imag'. ")


    freq = fftshift(fftfreq(zerofilling,np.mean(np.diff(t))))

    return freq, spec 
