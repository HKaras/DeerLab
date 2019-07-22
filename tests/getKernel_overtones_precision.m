function [err,data,maxerr] = test(opt,olddata)

%Check if implementation of kernel with overtones using the fresnel
%integrals equals the analytical kernel obtained by powder averaging
% is passes, Fresnel implementation is ok and the precision is as good as
% the Fresnel integrals can get.
TheoryKernel = [1.,-0.04445104927166716,-0.07755044305537568,0.07851607683975404,...
                0.036788014103474,-0.03400124912476483,-0.0472090401611318,...
                -0.04387503453950212,0.07709889223945138,0.0561564006520221,...
                0.02132186965158808,-0.01126891772078065,-0.02348189268499024,...
                -0.02921162944524985,-0.03037813625410701,-0.0376898903058106,...
                -0.04167686772343662,-0.03812301523329223,-0.03445203907857286,...
                -0.0339223232949867,-0.03470796433618248,-0.03449887585988132,...
                -0.03298429976682242,-0.03102408751361059,-0.02952116187223694,...
                -0.02898159340375473,-0.02948509409120466,-0.03078253761718941,...
                -0.03241789449104479,-0.03386466349863775,-0.03468970460640716,...
                -0.03473434253047652,-0.03424313872782415,-0.03381786219592736,...
                -0.03412588174057757,-0.03549233465139772,-0.03767424634393482,...
                -0.03997427724138708,-0.041512791332523,-0.04147020079631944,...
                -0.0394569855521979,-0.03602690935848631,-0.03262905033545368,...
                -0.03051881687677427,-0.02971537666948035,-0.02942990916166464,...
                -0.02921277535451182,-0.02888687974684233,-0.02767226855581926,...
                -0.02468431106429605,-0.02046159008500678,-0.01673116628670092,...
                -0.01419910137670651,-0.01154900057757849,-0.007015286548197135,...
                -0.0001042848144478248,0.00844030692077206,0.01735884927705575,...
                0.02520510166072932,0.03100264184331541,0.03535861867128369,...
                0.04050183676563213,0.04868580399639706,0.06060736567548223,...
                0.07514989754019091,0.089729425333304,0.100436554377009,...
                0.1027836575276323,0.0937960240149619,0.07408775664279487,...
                0.04779565126665569,0.02030437444416405,-0.004120550478013241,...
                -0.02310875905967178,-0.03575614794049643,-0.0422747395843624,...
                -0.04404648431105509,-0.04338778807680244,-0.04264338028155333,...
                -0.04318837765344592,-0.04512891498593397,-0.04776755368203892,...
                -0.05023487984305874,-0.05180114861740996,-0.05193174812008982,...
                -0.05039041529835111,-0.04743395251181136,-0.04383748049012921,...
                -0.04056779161325643,-0.03828431059393536,-0.03705787001735568,...
                -0.03651768019386782,-0.03625806954651103,-0.03613458800047519,...
                -0.03622317709490192,-0.03653909898564833,-0.03681179912146447,...
                -0.03653539936295003,-0.03526277251146228,-0.03291081161251739,...
                -0.0298450543907915];
TimeAxis = 0:6/100:6;
DistanceAxis = 2:4/100:6;
Tmix = 50; %us
T1 = 88; %us
overtones = getOvertoneCoeffs(5,Tmix,T1);

NumericalKernel = getKernel(TimeAxis,DistanceAxis,[],'OvertoneCoeffs',overtones);

NumericalKernel = diag(NumericalKernel)';

error = abs(NumericalKernel - TheoryKernel);
err = any(error>1e-13);
maxerr = max(error);

data = [];

end