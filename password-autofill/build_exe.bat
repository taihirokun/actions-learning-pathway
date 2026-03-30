@echo off
echo ========================================
echo  パスワード自動入力ツール - exe作成
echo  ※このbatはインターネット接続のある
echo    PCで実行してください。
echo ========================================
echo.
echo PyInstallerをインストール中...
pip install pyinstaller

echo.
echo exeファイルを作成中（外部ライブラリなし・標準ライブラリのみ）...
pyinstaller --onefile --windowed --name "パスワード自動入力ツール" password_autofill.py

echo.
echo ======================================
echo  完了！
echo  dist\パスワード自動入力ツール.exe
echo  を作成しました。
echo  このexeファイルだけをオフラインPCに
echo  コピーしてください。
echo ======================================
pause
