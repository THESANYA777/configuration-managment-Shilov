@echo off
cd /d "%~dp0.."
py -3 emulator.py --vfs-path .\\vfs\\multi.json --startup-script .\\scripts\\test_all.txt
