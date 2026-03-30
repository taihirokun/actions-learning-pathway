@echo off
REM Pythonが使える場合はそのまま起動（インストール不要）
python password_autofill.py
if errorlevel 1 (
    echo.
    echo Pythonが見つかりませんでした。
    echo 1. Python 3.x をインストールするか
    echo 2. build_exe.bat を実行してexeファイルを作成してください。
    pause
)
