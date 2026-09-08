@echo off
setlocal
if not defined CLAUDE_PROJECT_DIR (
  echo CLAUDE_PROJECT_DIR is not set >&2
  exit /b 1
)
"%CLAUDE_PROJECT_DIR%\.venv\Scripts\python.exe" "%CLAUDE_PROJECT_DIR%\tools\redesign_gate_hook.py"
exit /b %ERRORLEVEL%
