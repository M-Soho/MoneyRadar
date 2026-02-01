#!/bin/bash
# MoneyRadar Development Startup Script

set -e

echo "🚀 Starting MoneyRadar Development Environment"
echo "=============================================="
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "   Consider activating with: source venv/bin/activate"
    echo ""
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
    echo "✅ Frontend dependencies installed"
    echo ""
fi

# Initialize database if needed
if [ ! -f "moneyradar.db" ]; then
    echo "🗄️  Initializing database..."
    python init_db.py
    echo "✅ Database initialized"
    echo ""
fi

echo "Starting services..."
echo ""
echo "📍 API Server: http://localhost:5000"
echo "📍 Web UI: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"
echo "=============================================="
echo ""

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $(jobs -p) 2>/dev/null
    exit
}

trap cleanup EXIT INT TERM

# Start API server in background
echo "Starting API server..."
python -m monetization_engine.api.app &
API_PID=$!

# Give API time to start
sleep 3

# Start frontend dev server in background
echo "Starting Web UI..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for all background jobs
wait
