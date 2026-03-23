@echo off
chcp 65001
cls
echo ==========================================
echo   YOLOv26n模型复制工具
echo   用于复制训练好的模型到宇树Go2
echo ==========================================
echo.

:: 设置变量
set "MODEL_PATH=E:\port_segment\runs\segment\switch_port_seg_nano\weights\best.pt"
set "GO2_IP=192.168.1.100"
set "GO2_USER=go2"
set "REMOTE_PATH=/home/go2/inspection_system/models/yolo26n-seg.pt"

echo [INFO] 模型源路径: %MODEL_PATH%
echo [INFO] 目标机器狗IP: %GO2_IP%
echo.

:: 检查模型文件是否存在
if not exist "%MODEL_PATH%" (
    echo [ERROR] 模型文件不存在！
    echo [ERROR] 路径: %MODEL_PATH%
    echo.
    echo 请确认:
    echo 1. 模型训练已完成
    echo 2. 路径是否正确
    echo.
    pause
    exit /b 1
)

echo [OK] 模型文件已找到
echo.

:: 获取文件大小
for %%I in ("%MODEL_PATH%") do set "FILE_SIZE=%%~zI"
echo [INFO] 模型文件大小: %FILE_SIZE% bytes
echo.

:: 提示用户确认
echo 即将执行复制操作:
echo   从: %MODEL_PATH%
echo   到: %GO2_USER%@%GO2_IP%:%REMOTE_PATH%
echo.
set /p CONFIRM="确认复制? (Y/N): "
if /I not "%CONFIRM%"=="Y" (
    echo [INFO] 操作已取消
    pause
    exit /b 0
)

echo.
echo [INFO] 开始复制模型文件...
echo [INFO] 如果提示输入密码，请输入机器狗的SSH密码
echo.

:: 执行scp复制
scp "%MODEL_PATH%" %GO2_USER%@%GO2_IP%:%REMOTE_PATH%

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] 复制失败！
    echo.
    echo 可能的原因:
    echo 1. SSH连接失败 - 请检查IP地址和网络连接
    echo 2. 认证失败 - 请检查用户名和密码
    echo 3. 目标目录不存在 - 请先在Go2上创建目录
    echo.
    echo 你可以手动复制:
    echo   scp "%MODEL_PATH%" %GO2_USER%@%GO2_IP%:%REMOTE_PATH%
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] 模型复制成功！
echo.

:: 验证文件（可选）
echo [INFO] 正在验证远程文件...
ssh %GO2_USER%@%GO2_IP% "ls -lh %REMOTE_PATH%"

if %ERRORLEVEL% equ 0 (
    echo.
    echo [OK] 验证成功！模型已在Go2上就绪。
    echo.
    echo 下一步:
    echo 1. SSH连接到Go2: ssh %GO2_USER%@%GO2_IP%
    echo 2. 启动检测系统: ./start_inspection.sh
    echo 3. 在浏览器访问: http://%GO2_IP%:5000
) else (
    echo.
    echo [WARN] 无法验证远程文件，但复制可能已成功
)

echo.
pause
