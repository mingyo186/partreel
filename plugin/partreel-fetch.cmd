@echo off
rem PartReel Fetch - standalone launcher (no PCB editor needed).
rem ASCII ONLY in this file: cmd.exe parses batch files in the OEM codepage
rem (cp949 on Korean Windows), so UTF-8 Korean comments corrupt the parser
rem (2026-08-01 user report: garbled "not recognized" errors).
setlocal
set "PLUGDIR=%~dp0"

rem Find KiCad's bundled Python (newest version dir wins).
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
  echo KiCad Python not found. Please check your KiCad install path.
  echo Manual run: "<KiCad>\bin\pythonw.exe" -m partreel_fetch
  pause
  exit /b 1
)

start "" "%KIPY%" -c "import sys; sys.path.insert(0, r'%PLUGDIR%'); from partreel_fetch.__main__ import main; sys.exit(main(sys.argv[1:]))" %*
endlocal
