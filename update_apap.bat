
@echo off
setlocal

cd /d "%~dp0"

echo ============================================
echo APAP ANDMETE UUENDAMINE
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo VIGA: Pythoni virtuaalkeskkonda ei leitud.
    goto :error
)

set /p "SD_DRIVE=Sisesta SD-kaardi kettataht (nt E): "

if not defined SD_DRIVE (
    echo VIGA: Kettataht puudub.
    goto :error
)

set "SD_PATH=%SD_DRIVE%:\"

if not exist "%SD_PATH%DATALOG\" (
    echo VIGA: SD-kaardi DATALOG kausta ei leitud.
    echo Kontrolli kettatahise oigsust.
    goto :error
)

echo.
echo SD-kaart: %SD_PATH%
echo Andmete tootlemine algab...
echo.

".venv\Scripts\python.exe" "src\pipeline.py" --sd "%SD_PATH%"

if errorlevel 1 goto :error

echo.
echo ============================================
echo ANDMETE UUENDAMINE EDUKALT LOPETATUD
echo ============================================
goto :end

:error
echo.
echo ============================================
echo ANDMETE UUENDAMINE EBAONNESTUS
echo ============================================

:end
echo.
pause
endlocal
