@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"

rem 统一基于脚本所在目录定位项目根目录，避免中文路径和工作目录偏移导致的数据路径错误。
set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR=%ROOT_DIR%\frontend"
set "VENV_DIR=%ROOT_DIR%\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "BACKEND_STAMP_FILE=%VENV_DIR%\.backend-deps-installed"
set "FRONTEND_STAMP_FILE=%FRONTEND_DIR%\.frontend-deps-installed"

echo [INFO] Solo 一键启动脚本
echo [INFO] 项目根目录: %ROOT_DIR%

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 py 启动器，请先安装 Python Launcher。
  exit /b 1
)

py -3.11 --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 Python 3.11，请确认已安装 Python 3.11.4 并可通过 `py -3.11` 调用。
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 node，请先安装 Node.js 24。
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 npm，请确认 Node.js 安装完整。
  exit /b 1
)

call :check_port 8000
if errorlevel 1 exit /b 1
call :check_port 3000
if errorlevel 1 exit /b 1

if not exist "%VENV_PYTHON%" (
  echo [INFO] 正在创建 Python 3.11 虚拟环境...
  py -3.11 -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [ERROR] 虚拟环境创建失败。
    exit /b 1
  )
)

if not exist "%BACKEND_STAMP_FILE%" (
  echo [INFO] 正在升级 pip/setuptools/wheel...
  "%VENV_PYTHON%" -m pip install --upgrade pip setuptools wheel
  if errorlevel 1 (
    echo [ERROR] pip 基础工具升级失败。
    exit /b 1
  )

  echo [INFO] 正在安装后端依赖...
  pushd "%BACKEND_DIR%"
  "%VENV_PYTHON%" -m pip install -r requirements.txt
  set "PIP_EXIT=!ERRORLEVEL!"
  popd
  if not "!PIP_EXIT!"=="0" (
    echo [ERROR] 后端依赖安装失败。
    exit /b 1
  )

  >"%BACKEND_STAMP_FILE%" echo ok
) else (
  echo [INFO] 后端依赖未变化，跳过 pip install。
)

set "NEED_NPM_CI=0"
if not exist "%FRONTEND_DIR%\node_modules" (
  set "NEED_NPM_CI=1"
) else (
  if not exist "%FRONTEND_STAMP_FILE%" (
    set "NEED_NPM_CI=1"
  )
)

if "!NEED_NPM_CI!"=="1" (
  echo [INFO] 正在安装前端依赖...
  pushd "%FRONTEND_DIR%"
  npm ci
  set "NPM_EXIT=!ERRORLEVEL!"
  popd
  if not "!NPM_EXIT!"=="0" (
    echo [ERROR] 前端依赖安装失败。
    exit /b 1
  )

  >"%FRONTEND_STAMP_FILE%" echo ok
) else (
  echo [INFO] 前端依赖未变化，跳过 npm ci。
)

echo [INFO] 正在启动后端服务...
start "Solo Backend" /D "%BACKEND_DIR%" cmd /k "chcp 65001 >nul && set PYTHONUTF8=1 && ""%VENV_PYTHON%"" run.py"
if errorlevel 1 (
  echo [ERROR] 后端窗口启动失败。
  exit /b 1
)

echo [INFO] 正在等待后端服务就绪...
call :wait_port_ready 8000 30 后端服务
if errorlevel 1 exit /b 1

echo [INFO] 正在启动前端服务...
start "Solo Frontend" /D "%FRONTEND_DIR%" cmd /k "chcp 65001 >nul && set PYTHONUTF8=1 && npm run dev -- --host 127.0.0.1"
if errorlevel 1 (
  echo [ERROR] 前端窗口启动失败。
  exit /b 1
)

echo [INFO] 启动完成。
echo [INFO] 后端地址: http://127.0.0.1:8000
echo [INFO] 前端地址: http://127.0.0.1:3000
echo [INFO] 如需退出，请分别关闭 Solo Backend 与 Solo Frontend 窗口。
echo [INFO] 若 PDF 导出失败，请额外安装 wkhtmltopdf；当前代码会自动降级为 HTML。
exit /b 0

:check_port
powershell -NoProfile -Command "$port = %~1; $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue; if ($null -ne $listener) { exit 1 } else { exit 0 }" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 端口 %~1 已被占用，请先释放该端口后重试。
  exit /b 1
)
exit /b 0

:wait_port_ready
set "WAIT_PORT=%~1"
set "WAIT_SECONDS=%~2"
set "WAIT_NAME=%~3"
if not defined WAIT_SECONDS set "WAIT_SECONDS=30"
if not defined WAIT_NAME set "WAIT_NAME=服务"

for /l %%I in (1,1,!WAIT_SECONDS!) do (
  powershell -NoProfile -Command "$port = !WAIT_PORT!; $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue; if ($null -ne $listener) { exit 0 } else { exit 1 }" >nul 2>nul
  if not errorlevel 1 (
    echo [INFO] !WAIT_NAME! 已监听 !WAIT_PORT! 端口。
    exit /b 0
  )
  timeout /t 1 /nobreak >nul
)

echo [ERROR] !WAIT_NAME! 在 !WAIT_SECONDS! 秒内未监听 !WAIT_PORT! 端口，请检查对应窗口输出。
exit /b 1
