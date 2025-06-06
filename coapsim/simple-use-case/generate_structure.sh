#!/bin/bash

# Define the root directory for the project
ROOT_DIR="coap_thermostat"

echo "Creating project structure under '$ROOT_DIR/'..."

# --- Create Directories ---

echo "Creating directories..."
# The -p flag creates parent directories as needed and doesn't complain if they exist
mkdir -p "$ROOT_DIR" \
         "$ROOT_DIR/client" \
         "$ROOT_DIR/client/app" \
         "$ROOT_DIR/client/app/resources" \
         "$ROOT_DIR/server" \
         "$ROOT_DIR/server/app"

# Check if directory creation was successful (optional but good practice)
if [ $? -ne 0 ]; then
    echo "Error creating directories. Exiting."
    exit 1
fi
echo "Directories created."

# --- Create Empty Files ---

echo "Creating empty files..."
# The touch command creates empty files
touch "$ROOT_DIR/docker-compose.yml" \
      "$ROOT_DIR/requirements.txt" \
      "$ROOT_DIR/client/Dockerfile" \
      "$ROOT_DIR/client/app/config.py" \
      "$ROOT_DIR/client/app/resources/temperature.py" \
      "$ROOT_DIR/client/app/resources/status.py" \
      "$ROOT_DIR/client/app/resources/control.py" \
      "$ROOT_DIR/client/app/device.py" \
      "$ROOT_DIR/client/app/main.py" \
      "$ROOT_DIR/server/Dockerfile" \
      "$ROOT_DIR/server/app/config.py" \
      "$ROOT_DIR/server/app/model.py" \
      "$ROOT_DIR/server/app/service.py" \
      "$ROOT_DIR/server/app/client.py" \
      "$ROOT_DIR/server/app/main.py"

# Check if file creation was successful (optional)
if [ $? -ne 0 ]; then
    echo "Error creating files. Some files might be missing."
    # We don't exit here, directories might still be useful
fi

echo "Structure generation complete."