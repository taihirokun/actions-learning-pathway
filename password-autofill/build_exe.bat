@echo off
echo ========================================
echo  パスワード自動入力ツール - exe作成
echo ========================================
echo.

REM 必要なパッケージをインストール
pip install -r requirements.txt
pip install pyinstaller

echo.
echo exeファイルを作成中...
pyinstaller --onefile --windowed --name "パスワード自動入力ツール" password_autofill.py

echo.
echo 完了！dist フォルダに "パスワード自動入力ツール.exe" が作成されました。
echo ダブルクリックで起動できます。
pause
