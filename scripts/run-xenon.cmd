@echo off
.venv\Scripts\python.exe -m xenon --max-absolute B --max-modules B --max-average A -e "*/migrations/*" analysis bibliography field_data geodata laboratory orchestration prototype raster_data
