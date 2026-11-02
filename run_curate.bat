@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUNBUFFERED=1"

set "ROOT=%~dp0"
set "LOGDIR=%ROOT%logs"
set "OUTDIR=%ROOT%output"

if not exist "%LOGDIR%" mkdir "%LOGDIR%"
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

set "TS="
for /f "delims=" %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss" 2^>nul') do set "TS=%%T"
if not defined TS set "TS=unknown_%RANDOM%"
set "LOG=%LOGDIR%\run_%TS%.log"

forfiles /P "%LOGDIR%" /M "run_*.log" /D -14 /C "cmd /c del @path" >nul 2>nul

echo ===== curator started %DATE% %TIME% =====
echo log: %LOG%

if not exist "%ROOT%curate.py" (
    echo ERROR: curate.py not found
    pause
    exit /b 1
)
if not exist "%ROOT%config.yaml" (
    echo ERROR: config.yaml not found
    pause
    exit /b 1
)
if not exist "%ROOT%core" (
    echo ERROR: core\ not found
    pause
    exit /b 1
)

set "PY_EXE=python"
set "EMBED_DIR=%ROOT%py"
set "EMBED_EXE=%EMBED_DIR%\python.exe"
set "EMBED_PY_VER=3.12.8"
set "EMBED_URL=https://www.python.org/ftp/python/%EMBED_PY_VER%/python-%EMBED_PY_VER%-embed-amd64.zip"

python --version >nul 2>nul
if errorlevel 1 goto :use_embedded_python
set "SYS_PY_MINOR="
for /f "tokens=3 delims=. " %%V in ('python --version 2^>nul') do set "SYS_PY_MINOR=%%V"
if defined SYS_PY_MINOR if %SYS_PY_MINOR% LSS 12 goto :use_embedded_python
goto :embedded_python_ready
:use_embedded_python
echo WARNING: switching to embedded Python in %EMBED_DIR%\
set "PY_EXE=%EMBED_EXE%"
:embedded_python_ready

if /I "%PY_EXE%"=="python" goto :python_exe_ready

if exist "%EMBED_EXE%" goto :embedded_deps
echo Embedded Python not found in %EMBED_DIR% - downloading embeddable Python %EMBED_PY_VER%...
if not exist "%EMBED_DIR%" mkdir "%EMBED_DIR%"
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%EMBED_URL%' -OutFile '%TEMP%\python-embed.zip'"
powershell -NoProfile -Command "Expand-Archive -Path '%TEMP%\python-embed.zip' -DestinationPath '%EMBED_DIR%' -Force"
del "%TEMP%\python-embed.zip" >nul 2>nul
echo Embedded Python installed to %EMBED_DIR%\

:embedded_deps
echo [stage] embed-deps
"%EMBED_EXE%" -u "%ROOT%tools\bootstrap_python.py" --py-dir "%EMBED_DIR%"
if errorlevel 1 (
    echo ERROR: embedded Python bootstrap failed - PyYAML not installed in %EMBED_DIR%\
    if not defined NO_PAUSE pause
    exit /b 1
)
:python_exe_ready
echo [stage] python-exe %PY_EXE%

echo [stage] route
if not defined UI_PORT_RESOLVED set "UI_PORT_RESOLVED=8765"
if defined UI_PORT set "UI_PORT_RESOLVED=%UI_PORT%"
if not defined NO_UI if "%*"=="" set "UI_MODE=1"
echo %* | find /I "--ui" >nul && set "UI_MODE=1"
echo %* | find /I "--share" >nul && set "UI_MODE=1"
set "UI_SHARE_FLAG="
echo %* | find /I "--share" >nul && set "UI_SHARE_FLAG=--share"
if defined UI_MODE goto :ui_mode_body
goto :ui_mode_end
:ui_mode_body
echo [stage] ui-port
set "UI_PORT_RESOLVED=8765"
"%PY_EXE%" -X utf8 -c "import os; v=os.environ.get('UI_PORT','').strip(); print(int(v) if v else (__import__('yaml').safe_load(open(r'%ROOT%config.yaml',encoding='utf-8')) or {}).get('ui',{}).get('port',8765))" >"%TEMP%\ui_port.txt" 2>nul
if exist "%TEMP%\ui_port.txt" set /p UI_PORT_RESOLVED=<"%TEMP%\ui_port.txt"
del "%TEMP%\ui_port.txt" >nul 2>nul
if not defined UI_PORT_RESOLVED set "UI_PORT_RESOLVED=8765"
if not "%UI_PORT_RESOLVED%"=="8765" set "UI_PORT=%UI_PORT_RESOLVED%"
echo Starting UI server at http://127.0.0.1:%UI_PORT_RESOLVED%
start "" "http://127.0.0.1:%UI_PORT_RESOLVED%"
"%PY_EXE%" -u "%ROOT%web\server.py" %UI_SHARE_FLAG%
exit /b %errorlevel%
:ui_mode_end

echo [stage] cores
if not defined NO_UPDATE (
    if not exist "%ROOT%tools\update_cores.py" (
        echo WARNING: tools\update_cores.py not found - cores not checked
    ) else (
        "%PY_EXE%" -u "%ROOT%tools\update_cores.py" --log-file "%LOG%"
    )
)

echo [stage] profile
if not defined PROFILE (
    set "PROFILE=A"
    set /p "PROFILE=Speed test: [F]ull 3MB/10s (precise), [L]ight 1MB/5s (fast), or [A]uto-detect (default)? "
)
set "PROFILE=%PROFILE: =%"

set "PROFILE_ARG="
if /I "%PROFILE%"=="F" set "PROFILE_ARG=--speed-profile full"
if /I "%PROFILE%"=="L" set "PROFILE_ARG=--speed-profile light"

set "SKIP_MERGE="
echo %* | find /I "selftest"    >nul && set "SKIP_MERGE=1"
echo %* | find /I "ping-only"   >nul && set "SKIP_MERGE=1"
echo [stage] mode
if defined SKIP_MERGE goto :mode_ready

if not defined MODE (
    set "MODE=R"
    set /p "MODE=Working nodes: [R]eplace (default), [A]ppend, or [K]eep previous? "
)
:mode_ready
if not defined MODE set "MODE=R"
if defined MODE set "MODE=%MODE: =%"
if defined SKIP_MERGE set "MODE_LOG=service run - merge skipped"
if not defined SKIP_MERGE set "MODE_LOG=working nodes: %MODE%"
echo [%DATE% %TIME%] %MODE_LOG% >> "%LOG%"

echo [stage] backup
"%PY_EXE%" -u "%ROOT%curate.py" --backup-working --log-file "%LOG%"
if errorlevel 1 echo WARNING: working-nodes backup failed

echo [stage] pipeline
"%PY_EXE%" -u "%ROOT%curate.py" --log-file "%LOG%" %PROFILE_ARG% %*
set "RC=%errorlevel%"

if "%RC%"=="3" (
    echo WARNING: 0 working nodes - previous working_nodes.txt kept as-is
    if exist "%OUTDIR%\working_nodes.prev.txt" del "%OUTDIR%\working_nodes.prev.txt" >nul 2>nul
    goto :finish
) else (
    if not "%RC%"=="0" (
        echo ERROR: curate.py exited with code %RC%, log: %LOG%
        if not defined NO_PAUSE pause
        exit /b %RC%
    )
)

echo [stage] apply-mode %MODE%
if defined SKIP_MERGE set "MODE=none"
if /I "%MODE%"=="A" set "MODE=append"
if /I "%MODE%"=="K" set "MODE=keep"
if /I "%MODE%"=="R" set "MODE=replace"
if /I not "%MODE%"=="replace" if /I not "%MODE%"=="append" if /I not "%MODE%"=="keep" if /I not "%MODE%"=="none" set "MODE=replace"
"%PY_EXE%" -u "%ROOT%curate.py" --apply-mode "%MODE%" --log-file "%LOG%"
set "APPLY_RC=%errorlevel%"
if "%APPLY_RC%"=="3" echo WARNING: apply-mode failed - keeping fresh list, backup kept


:finish
echo [stage] finish
del "%ROOT%temp\curate_resume.json" >nul 2>nul
echo.
echo ===== done =====
if exist "%OUTDIR%\working_nodes.txt" for /f %%C in ('find /c /v "" ^< "%OUTDIR%\working_nodes.txt"') do echo Working nodes: %%C
if exist "%OUTDIR%\subscription_url.txt" type "%OUTDIR%\subscription_url.txt"
echo Log: %LOG%
echo Flags: no args = UI http://127.0.0.1:8765 ^| --ui explicit UI ^| --report full run ^| --selftest ^| --tcping-only ^| --ping-only ^| --only vless,trojan ^| --speed-profile full^|light
echo UI: no args - UI in browser (%UI_PORT_RESOLVED% by default); NO_UI=1 - console path with bars in the window
echo Mode: asked BEFORE the scan ^(R=replace default, A=append, K=keep^). For unattended: set "MODE=A" before launch
echo Profile: set "PROFILE=L" before launch, no question ^(F/L = full 3MB / light 1MB, A=auto^)
echo Cores: Xray and sing-box are checked before the scan - Y/n asks, "NO_UPDATE=1" skips, "UPDATE_YES=1" updates without a question
if not defined NO_PAUSE pause
exit /b %RC%

exit /b
