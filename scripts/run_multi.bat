@echo off
cd /d "%~dp0.."
py -3 shell_emulator.py --vfs-path .\\vfs\\multi.json --startup-script .\\scripts\\test_all.txt
