#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 shell_emulator.py --vfs-path ./vfs/multi.json --startup-script ./scripts/test_all.txt
