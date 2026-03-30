@echo off
REM Start the NutriAgent web server with chat UI
REM Access at: http://localhost:8000

echo Starting NutriAgent Web Server...
echo.
echo Chat UI will be available at: http://localhost:8000
echo API docs available at: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

call venv\Scripts\activate.bat
python app.py
