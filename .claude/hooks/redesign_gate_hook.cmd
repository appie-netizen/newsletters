@echo off
REM Portable launcher for the redesign hard-gates hook (PowerShell / cmd path).
REM Only needed when Claude Code runs hooks without Git Bash; the default is
REM .claude/hooks/redesign_gate_hook.sh . Same interpreter order:
REM   1. project venv (.venv\Scripts\python.exe)  2. py -3  3. python
REM Gate scripts are stdlib-only. Exit 0 when no Python is found so a missing
REM interpreter never wedges the session.
setlocal

set "ROOT=%CLAUDE_PROJECT_DIR%"
if not defined ROOT set "ROOT=%~dp0..\.."
set "SCRIPT=%ROOT%\tools\redesign_gate_hook.py"

if exist "%ROOT%\.venv\Scripts\python.exe" (
  "%ROOT%\.venv\Scripts\python.exe" "%SCRIPT%"
  exit /b %ERRORLEVEL%
)
where py >nul 2>&1 && (
  py -3 "%SCRIPT%"
  exit /b %ERRORLEVEL%
)
where python >nul 2>&1 && (
  python "%SCRIPT%"
  exit /b %ERRORLEVEL%
)
echo redesign_gate_hook: no Python 3 interpreter found - gates not run >&2
exit /b 0
