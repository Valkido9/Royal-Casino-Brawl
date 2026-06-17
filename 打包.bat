@echo off
setlocal

:: --- 1. 这里设置你的版本号 ---
set VERSION=0.4.0

:: --- 2. 这里设置 exe 的名称 ---
set GAME_NAME=任地狱明星大乱斗

echo 正在打包版本: v%VERSION%...
:: 自动执行打包命令 (建议使用 -D 目录模式，比 --onefile 启动快得多)
pyinstaller -D -w main.py

echo 打包完成，正在同步资源...
xcopy /E /I /Y "assets" "dist\main\assets\"
xcopy /E /I /Y "sounds" "dist\main\sounds\"

:: --- 3. 自动重命名并打包成发布包 ---
echo 正在准备发布文件...
ren "dist\main\main.exe" "%GAME_NAME%_v%VERSION%.exe"

:: 这里使用 powershell 创建一个 zip 压缩包，方便你发给朋友
powershell Compress-Archive -Path "dist\main\*" -DestinationPath "发布包_%GAME_NAME%_v%VERSION%.zip" -Force

echo.
echo ===================================================
echo 构建成功！
echo 请查看根目录下的: 发布包_%GAME_NAME%_v%VERSION%.zip
echo ===================================================
pause