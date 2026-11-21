@echo off
chcp 65001 > nul
echo ===================================================
echo  電力運用シミュレータ (PowerGridSim) exe化スクリプト
echo ===================================================

call conda activate GameEmv
if errorlevel 1 (
    echo [ERROR] conda activate GameEmv に失敗しました。
    pause
    exit /b 1
)

python build_exe.py
if errorlevel 1 (
    echo [ERROR] ビルド中にエラーが発生しました。
    pause
    exit /b 1
)

echo.
echo ビルドが正常に終了しました。
pause