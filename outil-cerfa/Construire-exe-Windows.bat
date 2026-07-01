@echo off
REM ================================================================
REM  Fabrique le fichier .exe autonome (Python plus necessaire ensuite).
REM  A lancer sur une machine Windows. Le resultat est dans dist\CERFA-MML.exe
REM ================================================================
cd /d "%~dp0"
echo Installation de PyInstaller...
python -m pip install pyinstaller
echo.
echo Construction de l'executable...
pyinstaller --onefile --windowed --name "CERFA-MML" --add-data "modeles;modeles" app.py
echo.
echo Termine. L'application se trouve dans le dossier dist\CERFA-MML.exe
echo Placez config.json a cote de CERFA-MML.exe avant de l'utiliser.
pause
