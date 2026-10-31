@echo off
echo === Тест 1: без параметров ===
python emulator.py
echo.
echo === Тест 2: только VFS path ===
python emulator.py --vfs-path .\vfs_only
echo.
echo === Тест 3: VFS path + startup script ===
python emulator.py --vfs-path .\vfs_both --startup-script .\startup.bat
