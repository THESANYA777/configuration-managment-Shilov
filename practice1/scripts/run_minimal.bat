@echo off
cd /d "%~dp0.."
py -3 emulator.py --vfs-path .\\vfs\\minimal.json --startup-script .\\scripts\\test_all.txt
