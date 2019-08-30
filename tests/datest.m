% datest    Testing engine for DeerAnalysis
%
%   Usage:
%     datest            run all tests
%     datest adsf       run all tests whose name starts with asdf
%     datest asdf d     run all tests whose name starts with asdf and
%                       display results
%     datest asdf r     evaluate all tests whose name starts with asdf and
%                       recalculate and store regression data
%     datest asdf t     evaluate all tests whose name starts with asdf and
%                       report timings
%
%   Either the command syntax as above or the function syntax, e.g.
%   datest('asdf','t'), can be used.
%
%   Run all tests including timings:   datest('*','t')
%
%   All test files must have an underscore _ in their filename.

function out = datest(TestName,params)

% Check whether DeerAnalysis is on the Matlab path
DeerAnalysisPath = fileparts(which('DeerAnalysis'));
if isempty(DeerAnalysisPath)
  error('DeerAnalysis is not on the Matlab path!');
end

fid = 1; % output to command window

%Check for missing input arguments
if nargin<1
  TestName = '';
end
if nargin<2
  params = '';
end

Opt.Display = any(params=='d');
Opt.Regenerate = any(params=='r');
Opt.Verbosity = Opt.Display;

displayErrors = any(params=='p');
displayTimings = any(params=='t');

if Opt.Display && displayTimings
  error('Cannot plot test results and report timings at the same time.');
end

if any(TestName=='_')
    FileMask = [TestName '*.m'];
elseif strcmp(TestName,'all')
    FileMask = '*_*.m';
else
    FileMask = [TestName '*_*.m'];
end

%Look for test in the \tests directory of DeerAnalysis
FileList = dir(fullfile(DeerAnalysisPath,'tests',FileMask));

if numel(FileList)==0
  error('No test functions matching the pattern %s',FileMask);
end

TestFileNames = sort({FileList.name});

fprintf(fid,'=======================================================================\n');
fprintf(fid,'DeerAnalysis test set                      %s\n(Matlab %s)\n',datestr(now),version);
fprintf(fid,'DeerAnalysis location: %s\n',DeerAnalysisPath);
fprintf(fid,'=======================================================================\n');
fprintf(fid,'Display: %d, Regenerate: %d, Verbosity: %d\n',...
  Opt.Display,Opt.Regenerate, Opt.Verbosity);
fprintf(fid,'-----------------------------------------------------------------------\n');

% Codes for test outcomes:
%    0   test passed
%   +1   test failed
%   +2   test crashed
%   +3   not tested

OutcomeStrings = {'pass','failed','crashed','not tested'};

%==========================================================================
%Loop over all tests to be run
%==========================================================================
for iTest = 1:numel(TestFileNames)
  
  if Opt.Display
    clf; drawnow;
  end

  thisTest = TestFileNames{iTest}(1:end-2);

  
  % Load, or regenerate, comparison data
  olddata = [];
  TestDataFile = ['data/' thisTest '.mat'];
  if exist(TestDataFile,'file')
    if Opt.Regenerate
      delete(TestDataFile);
      olddata = [];
    else
      try
        olddata = load(TestDataFile,'data');
        olddata = olddata.data;
      catch
        error('Could not load data for test ''%s''.',thisTest);
      end
    end
  end
  
  %Clear data in the cache before testing
  Pos = strfind(thisTest,'_');
  functionName = thisTest(1:Pos(1)-1);
  clear(functionName)
  
  % Run test, catch any errors
  tic
  try
      if displayErrors
          [err,data,maxerr(iTest)] = feval(thisTest,Opt,olddata);
      else
          [err,data] = feval(thisTest,Opt,olddata);
      end
    % if test returns empty err, then treat it as not tested
    if isempty(err)
      err = 3; % not tested
    else
      err = any(err~=0);
    end
    errorInfo = [];
    errorStr = '';
  catch exception
    data = [];
    err = 2;
    errorInfo = exception;
    errorStr = getReport(errorInfo);
    errorStr = ['    ' regexprep(errorStr,'\n','\n    ') char(10)];
  end
  time_used(iTest) = toc;
  
  isRegressionTest = ~isempty(data);
  saveTestData = isRegressionTest && isempty(olddata);  
  if saveTestData
    save(TestDataFile,'data');
  end
  
  testResults(iTest).err = double(err);
  testResults(iTest).err = double(err);
  testResults(iTest).name = thisTest;
  testResults(iTest).errorData = errorInfo;
  
  outcomeStr = OutcomeStrings{testResults(iTest).err+1};
  
  if ~isempty(data)
    typeStr = 'regression';
  else
    typeStr = 'direct';
  end
  
  if displayTimings
    timeStr = sprintf('%0.3f seconds',time_used(iTest));
  else
    timeStr = [];
  end
  
  try
      if displayErrors
          maxerrStr = sprintf('%0.2e ',maxerr(iTest));
      else
          maxerrStr = [];
      end
  catch
      maxerrStr = [];
  end
  str = sprintf('%-36s  %-12s%-8s%s%s\n%s',...
       testResults(iTest).name,typeStr,outcomeStr,maxerrStr,timeStr,errorStr);
  str(str=='\') = '/';
  
  testResults(iTest).msg = str;
  
  fprintf(fid,str);
    if Opt.Display
      if iTest<numel(TestFileNames), pause; end
    end
end

allErrors = [testResults.err];

% Display timings of slowest tests
if displayTimings
  fprintf(fid,'-----------------------------------------------------------------------\n');
  fprintf(fid,'Total test time:                        %7.3f seconds\n',sum(time_used));
  fprintf(fid,'Slowest tests:\n');
  [time,iTest] = sort(time_used,'descend');
  for q = 1:min(10,numel(time))
    fprintf(fid,'%-36s    %7.3f seconds\n',testResults(iTest(q)).name,time(q));
  end
end

% Display all tests that failed or crashed
if any(allErrors==1) || any(allErrors==2)
  fprintf(fid,'-----------------------------------------------------------------------\n');
  for iTest = find(allErrors)
    fprintf(fid,testResults(iTest).msg);
  end
end

fprintf(fid,'-----------------------------------------------------------------------\n');
msg = sprintf('%d passes, %d failures, %d crashes\n',sum(allErrors==0),sum(allErrors==1),sum(allErrors==2));
fprintf(fid,msg);
fprintf(fid,'-----------------------------------------------------------------------\n');

% Return output if desired
if nargout==1
  out.Results = testResults;
  out.outcomes = allErrors;
end

return
