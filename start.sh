#!/bin/sh
PUID=${PUID:-1000}
PGID=${PGID:-1000}

echo "Starting Container with $PUID:$PGID permissions..."

if [ "$PUID" = "0" ]; then
    echo "Running as root user"
    USER_HOME="/root"
    mkdir -p "$USER_HOME"
else
    if ! echo "$PUID" | grep -qE '^[0-9]+$'; then
        echo "PUID is not a valid integer. Exiting..."
        exit 1
    fi
    
    if ! echo "$PGID" | grep -qE '^[0-9]+$'; then
        echo "PGID is not a valid integer. Exiting..."
        exit 1
    fi

    USERNAME=${USERNAME:-ragnar}
    GROUPNAME=${GROUPNAME:-ragnar}
    USER_HOME="/home/$USERNAME"

    if ! getent group "$PGID" > /dev/null; then
        addgroup "$GROUPNAME"
        if [ $? -ne 0 ]; then
            echo "Failed to create group. Exiting..."
            exit 1
        fi
    else
        GROUPNAME=$(getent group "$PGID" | cut -d: -f1)
    fi

    mkdir -p "$USER_HOME"

    if ! getent passwd "$USERNAME" > /dev/null; then
        adduser --disabled-password --gecos "" --home "$USER_HOME" --ingroup "$GROUPNAME" "$USERNAME"
        if [ $? -ne 0 ]; then
            echo "Failed to create user. Exiting..."
            exit 1
        fi
    else
        if [ "$PUID" -ne 0 ]; then
            usermod -u "$PUID" -g "$PGID" "$USERNAME"
            if [ $? -ne 0 ]; then
                echo "Failed to modify user UID/GID. Exiting..."
                exit 1
            fi
        else
            echo "Skipping usermod for root user."
        fi
    fi
    
    chown -R "$PUID:$PGID" "$USER_HOME"
    chown -R "$PUID:$PGID" /app/data
fi

umask 002

export XDG_CONFIG_HOME="$USER_HOME/.config"
export XDG_DATA_HOME="$USER_HOME/.local/share"
export POETRY_CACHE_DIR="$USER_HOME/.cache/pypoetry"
export HOME="$USER_HOME"

export PATH="$PATH:/app/.venv/bin"

echo "Container Initialization complete."

echo "Starting Ragnar..."
if [ "$PUID" = "0" ]; then
    ollama serve &
    OLLAMA_PID=$!
    sleep 5
    cd /app && poetry run python src/main.py &
    PYTHON_PID=$!
else
    su "$USERNAME" -c "ollama serve" &
    OLLAMA_PID=$!
    sleep 5
    su "$USERNAME" -c "cd /app && poetry run python src/main.py" &
    PYTHON_PID=$!
fi

trap "kill $OLLAMA_PID $PYTHON_PID 2>/dev/null" EXIT

wait $OLLAMA_PID $PYTHON_PID
