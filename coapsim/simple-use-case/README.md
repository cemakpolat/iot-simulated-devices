
---
# Use Case: Smart Thermostat with AI Control
In this project, we simulate a CoAP-enabled thermostat device with multiple RESTful resources. An AI-powered backend polls the device and makes real-time HVAC control decision using lightweight logic.

## Prerequisites

Make sure you have:
- Docker
- Docker-compose

## Quick Start

This bash script (`coap_starter.sh`) simplifies managing your Docker Compose services by the following methods:

1.  **Make it executable:**
    ```bash
    chmod +x coap_starter.sh
    ```

## Usage

Run the script with the desired command:

* **Start services:**
    ```bash
    ./coap_starter.sh start
    ```

* **Stop services & optionally clean volumes:**
    ```bash
    ./coap_starter.sh stop
    ```

* **Restart services:**
    ```bash
    ./coap_starter.sh restart
    ```

* **Clean volumes only:**
    ```bash
    ./coap_starter.sh clean
    ```

* **Watch logs (live stream):**
    ```bash
    ./coap_starter.sh watch
    ```
    (Press `Ctrl+C` to stop watching.)

