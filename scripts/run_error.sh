#!/bin/sh
cd "$(dirname "$0")/.." || exit 1
python3 -m src.main --vfs vfs/files.json --script scripts/errors.txt
