#!/bin/sh
rm -rf build dist *.spec *.zip
wine C:/Python36-32/Scripts/pyinstaller.exe --onefile ../app/openocd_svd.py
zip -j openocd_svd_v$1_win32.zip dist/openocd_svd.exe