%
% RD_ONEGAUSSIAN Gaussian distribution parametric model
%
%   info = RD_ONEGAUSSIAN
%   Returns an (info) structure containing the specifics of the model.
%
%   P = RD_ONEGAUSSIAN(r,param)
%   Computes the N-point model (P) from the N-point distance axis (r) according to 
%   the paramteres array (param). The required parameters can also be found 
%   in the (info) structure.
%
% PARAMETERS
% name    symbol default lower bound upper bound
% --------------------------------------------------------------------------
% param(1)  <r>    3.5     1.0         20         mean distance
% param(2)   w     0.5     0.2         5           FWHM
% --------------------------------------------------------------------------
%
% Copyright(C) 2019  Luis Fabregas, DeerAnalysis2
%
% This program is free software: you can redistribute it and/or modify
% it under the terms of the GNU General Public License 3.0 as published by
% the Free Software Foundation.

function output = rd_onegaussian(r,param)

nParam = 2;

if nargin==0
    %If no inputs given, return info about the parametric model
    info.Model  = 'Single Gaussian distribution';
    info.Equation  = ['exp(-(r-<r>)�/(',char(963),'*sqrt(2))�)'];
    info.nParam  = nParam;
    info.parameters(1).name = 'Mean distance <r>';
    info.parameters(1).range = [1 20];
    info.parameters(1).default = 3.5;
    info.parameters(1).units = 'nm';
    
    info.parameters(2).name = 'FWHM w';
    info.parameters(2).range = [0.2 5];
    info.parameters(2).default = 0.5;
    info.parameters(2).units = 'nm';
    
    output = info;
    return
end

if nargin~=2
    error('Model requires two input arguments.')
end

% Assert that the number of parameters matches the model
if length(param)~=nParam
  error('The number of input parameters does not match the number of model parameters.')
end

% Compute the model distance distribution
P = exp(-((r(:)-param(1))/param(2)).^2);
dr = r(2)-r(1);
P = P/sum(P)/dr;
output = P;

return