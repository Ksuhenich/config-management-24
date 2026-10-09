#!/bin/sh
cd "$(dirname "$0")/.." || exit 1
python3 -m src.main --vfs vfs/minimal.json --script scripts/quotes.txt
