@echo off
setlocal EnableDelayedExpansion

set "COLOR_GREEN=[92m"
set "COLOR_NC=[0m"

echo Starting black
poetry run black .
echo OK

echo Starting isort
poetry run isort .
echo OK

echo Starting mypy
poetry run mypy .
echo OK

echo Starting test with coverage
poetry run coverage run -m pytest
poetry run coverage report -m

echo %COLOR_GREEN%All tests passed successfully!%COLOR_NC%