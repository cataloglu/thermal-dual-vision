@echo off
REM Automatic backup script for Smart Motion Detector v2

set BACKUP_DIR=backups\%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%
set BACKUP_DIR=%BACKUP_DIR: =0%

echo Creating backup directory: %BACKUP_DIR%
mkdir "%BACKUP_DIR%" 2>nul

echo Backing up database...
copy data\app.db "%BACKUP_DIR%\app.db" >nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Database backup failed!
    exit /b 1
)

echo Backing up config...
copy data\config.json "%BACKUP_DIR%\config.json" >nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Config backup failed!
    exit /b 1
)

echo Backing up media...
xcopy data\media "%BACKUP_DIR%\media\" /E /I /Q >nul
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Media backup incomplete (may not exist yet)
)

echo.
echo ========================================
echo Backup COMPLETE!
echo ========================================
echo Location: %BACKUP_DIR%
echo Files:
echo   - app.db (cameras + events)
echo   - config.json (settings)
echo   - media/ (collage/MP4)
echo ========================================
echo.

pause
