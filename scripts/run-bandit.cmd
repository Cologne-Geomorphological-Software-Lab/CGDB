@echo off
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r analysis bibliography field_data geodata laboratory orchestration prototype raster_data
