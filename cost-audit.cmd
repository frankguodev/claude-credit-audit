@echo off
setlocal
rem Convenience launcher: run without installing (sets PYTHONPATH to bundled src).
rem Usage: cost-audit <repo-path> --plan max5x [more flags]
rem Install properly instead:  pip install .   then use the `cost-audit` command.
rem Override the interpreter by setting COST_AUDIT_PY to a python.exe path.
set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%src"
set "PY=%COST_AUDIT_PY%"
if not defined PY (
  for %%P in (py python python3) do if not defined PY (where %%P >nul 2>nul && set "PY=%%P")
)
if not defined PY (
  echo Python 3.10+ not found on PATH. Install it, set COST_AUDIT_PY, or: pip install . ^&^& cost-audit ...
  exit /b 1
)
%PY% -m cost_audit.cli %*
