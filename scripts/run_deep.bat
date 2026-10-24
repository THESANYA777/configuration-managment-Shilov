@echo off
cd /d "%~dp0.."
py -3 shell_emulator.py --vfs-path .\\vfs\\deep.json --startup-script .\\scripts\\test_all.txt
