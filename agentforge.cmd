@echo off
where py >nul 2>nul
if not errorlevel 1 goto use_py
where python >nul 2>nul
if not errorlevel 1 goto use_python
echo AgentForge requires Python 3.9 or newer. 1>&2
exit /b 1

:use_py
py -3 "%~dp0scripts\agentforge.py" %*
exit /b %errorlevel%

:use_python
python "%~dp0scripts\agentforge.py" %*
exit /b %errorlevel%
