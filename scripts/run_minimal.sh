#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 emulator.py --vfs-path ./vfs/minimal.json --startup-script ./scripts/test_all.txt
