@echo off
REM ================================================================
REM  Installation, a lancer UNE SEULE FOIS sur la machine Windows.
REM  Installe les composants necessaires a l'application.
REM ================================================================
cd /d "%~dp0"
echo Installation des composants (PyMuPDF, requests, requests_oauthlib)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Termine. Vous pouvez maintenant double-cliquer sur Lancer-CERFA.bat
pause
