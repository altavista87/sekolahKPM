#!/bin/bash
#
# EduSync Local UI/UX Testing Server
# Simple static server for testing without backend
#

set -e

PORT="${PORT:-8080}"
DIRECTORY="${DIRECTORY:-static}"

echo "🧪 EduSync Local UI/UX Test Server"
echo "=================================="
echo ""

# Check if Python is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python not found. Please install Python 3."
    exit 1
fi

echo "✓ Using Python: $PYTHON_CMD"
echo "✓ Serving directory: $DIRECTORY"
echo "✓ Port: $PORT"
echo ""
echo "📱 URLs:"
echo "   Main site:     http://localhost:$PORT"
echo "   UI Test Panel: http://localhost:$PORT/test-ui.html"
echo ""
echo "Press Ctrl+C to stop"
echo "=================================="
echo ""

# Change to directory and start server
cd "$DIRECTORY"

# Start Python HTTP server
if $PYTHON_CMD -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)" 2>/dev/null; then
    # Python 3.7+ - use --directory flag
    $PYTHON_CMD -m http.server $PORT
else
    # Older Python - serve from current directory
    $PYTHON_CMD -m http.server $PORT
fi
