@echo off
chcp 65001 > nul
REM Pythonが入っていればそのまま起動（外部ライブラリ不要・完全オフライン）
python password_autofill.py
if errorlevel 1 (
    echo.
    echo Pythonが見つかりません。
    echo 以下のどちらかを実行してください：
    echo.
    echo  [方法1] Python 3.x をインストールしてこのbatを再実行
    echo  [方法2] インターネットに繋がるPCで build_exe.bat を実行し
    echo          できあがった exe ファイルをこのPCにコピー
    echo.
    pause
)
