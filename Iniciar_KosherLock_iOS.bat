@echo off
title KosherLock iOS - Gestor de iPhones Kosher
cd /d "%~dp0"

if exist "KosherLock_iOS.exe" (
    start "" "KosherLock_iOS.exe"
    exit
)

python src\main.py
