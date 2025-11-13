@echo off

uv run alembic revision --autogenerate -m "temp"
uv run alembic upgrade head

REM Xóa file migration vừa tạo (giữ lại __pycache__ nếu có)
for /f %%F in ('dir /b alembic\versions\*.py ^| findstr /v __pycache__') do del "alembic\versions\%%F"

echo Done!