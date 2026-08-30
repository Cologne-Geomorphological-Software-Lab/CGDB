@echo off
.venv\Scripts\python.exe -m vulture analysis bibliography field_data geodata laboratory orchestration prototype raster_data vulture_whitelist.py --min-confidence 80
