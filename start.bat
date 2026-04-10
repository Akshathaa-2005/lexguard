@echo off
echo 🚀 Starting LexGuard Platform...

REM Start Backend Server
echo 📡 Starting Flask Backend...
cd backend
start "Backend" python app.py

REM Wait for backend to start
timeout /t 5 /nobreak

REM Start Frontend Server
echo 🎨 Starting Next.js Frontend...
cd ../frontend
start "Frontend" npm run dev

echo.
echo ✅ LexGuard Platform is running!
echo 🌐 Frontend: http://localhost:3000
echo 🔧 Backend: http://localhost:5000
echo.
echo Press any key to exit...
pause
