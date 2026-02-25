#!/bin/bash

APP_NAME="baclink"
APP_DIR="/opt/$APP_NAME"
VENV="$APP_DIR/venv"

PIDFILE="$APP_DIR/$APP_NAME.pid"
LOGFILE="$APP_DIR/$APP_NAME.log"

cd "$APP_DIR" || exit 1

echo "Starting $APP_NAME..."

# --------------------------------------------------
# Stop existing instance if running
# --------------------------------------------------
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    echo "Found pid $OLD_PID"
    if [ -d "/proc/$OLD_PID" ]; then
        echo "Stopping existing instance (PID $OLD_PID)..."
        kill "$OLD_PID"

        # wait up to 10 seconds
        for i in {1..10}; do
            if ! ps -p "$OLD_PID" > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done

        # force kill if needed
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            echo "Force killing..."
            kill -9 "$OLD_PID"
        fi
    fi

    rm -f "$PIDFILE"
fi

# --------------------------------------------------
# Start in background
# --------------------------------------------------
nohup $VENV/bin/python -m $APP_NAME >> "$LOGFILE" 2>&1 &

NEW_PID=$!
echo $NEW_PID > "$PIDFILE"

echo "$APP_NAME started (PID $NEW_PID)"
