@echo off
REM ================================================================
REM  Lance l'application CERFA (Windows).
REM  Double-cliquer sur ce fichier ouvre la fenetre de l'outil.
REM  Necessite Python installe (voir Installer-Windows.bat une fois).
REM ================================================================
cd /d "%~dp0"
python app.py
if errorlevel 1 (
  echo.
  echo Une erreur est survenue. Verifiez que Python est installe
  echo et que Installer-Windows.bat a bien ete lance une fois.
  pause
)
