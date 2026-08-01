@echo off
rem PartReel Fetch - PCB 편집기 없이 바로 실행 (회로도 그리는 중에 부품 가져오기)
rem 이 파일이 있는 폴더 = 플러그인 설치 폴더. KiCad 동봉 파이썬으로 실행한다.
setlocal
set "PLUGDIR=%~dp0"

rem KiCad 파이썬 찾기 (설치 경로 후보 순회)
set "KIPY="
for %%D in (
  "%ProgramFiles%\KiCad"
  "%ProgramFiles(x86)%\KiCad"
  "C:\Program Files\KiCad"
  "D:\Program Files\KiCad"
) do (
  if not defined KIPY (
    for /f "delims=" %%P in ('dir /b /o-n "%%~D" 2^>nul') do (
      if not defined KIPY if exist "%%~D\%%P\bin\pythonw.exe" set "KIPY=%%~D\%%P\bin\pythonw.exe"
    )
  )
)

if not defined KIPY (
  echo KiCad 파이썬을 찾지 못했습니다. KiCad 설치 경로를 확인하세요.
  echo 수동 실행: "＜KiCad＞\bin\pythonw.exe" -m partreel_fetch
  pause
  exit /b 1
)

start "" "%KIPY%" -c "import sys; sys.path.insert(0, r'%PLUGDIR%'); from partreel_fetch.__main__ import main; sys.exit(main(sys.argv[1:]))" %*
endlocal
