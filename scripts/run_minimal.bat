@echo off
cd /d "%~dp0.."
python -m src.main --vfs vfs/minimal.json --script scripts/quotes.txt
