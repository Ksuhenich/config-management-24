@echo off
cd /d "%~dp0.."
python -m src.main --vfs vfs/nested.json --script scripts/demo.txt
