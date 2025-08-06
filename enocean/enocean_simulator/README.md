
# EnOcean IoT Device Simulator

A comprehensive, asynchronous Python-based simulator for generating realistic EnOcean (ESP3) protocol data streams.

This tool is designed to emulate a wide variety of EnOcean devices, making it an invaluable asset for developing, testing, and demonstrating IoT applications without the need for physical hardware.
This simulator creates a virtual EnOcean gateway that populates a pseudo-terminal (PTY) with a realistic stream of data from different types of virtual devices. 
Your application can simply connect to this PTY as if it were a real serial hardware gateway.  

### Key Features

- **Pre-configured Devices:** Simulates a wide range of sensors and actuators, from temperature and humidity sensors to rocker switches and people counters.
- **Asynchronous & High-Performance:** Built with Python's `asyncio` for efficient handling of many devices.
- **Realistic Data Generation:** Each device type has a dedicated data generator that produces logical and time-varying values (e.g., lower light levels at night).
- **Correct Protocol Framing:** Implements the EnOcean ESP3 protocol, including correct packet structure and CRC8 checksum calculations.
- **Comprehensive Logging & Analysis:** Includes an enhanced `GatewayReceiver` that logs all incoming data to structured files (raw, decoded, CSV, JSON stats) and a `LogAnalyzer` tool to inspect and report on captured sessions.
- **Zero Hardware Required:** Runs on any Linux or macOS system, using a pseudo-terminal (PTY) to mimic a serial port.

## System Architecture

The simulator operates in two main parts: a **Sender** and a **Receiver**. I

1.  **The Simulator (Sender):**
    *   The `main.py` script orchestrates the simulation.
    *   It initializes a `SimulatorManager`, which in turn starts a `GatewaySender`.
    *   The `GatewaySender` creates a virtual serial port (a PTY, e.g., `/dev/ttys008`).
    *   Virtual devices defined in main.py are added to a `DeviceManager`.
    *   An `asyncio` loop periodically checks which devices are due to transmit.
    *   For each ready device, a `DataGenerator` creates a new, realistic data payload based on its EEP (EnOcean Equipment Profile).
    *   The `ESP3Protocol` class wraps this payload in a valid ESP3 telegram with correct headers and checksums.
    *   This telegram is written to the virtual serial port, ready for a client to read.

2.  **The Client (Receiver):**
    *   This can be **your own application** or the provided `GatewayReceiver` for testing and data capture. By default,`GatewayReceiver` is deactivated. 
    *   The client connects to the slave end of the virtual serial port.
    *   It reads the raw byte stream, identifies complete ESP3 telegrams, and verifies their checksums.
    *   Using a `DeviceManager` to map sender IDs to EEPs, it passes the payload to the `EEPDecoder`.
    *   The `EEPDecoder` translates the raw bytes into human-readable JSON (e.g., `{"temperature": 22.5, "humidity": 45.1}`).
    *   The provided `GatewayReceiver` saves all this data to log files for later analysis.

 
*(See Mermaid diagram below for the source)*

## Getting Started

### Prerequisites

-   Python 3.8+
-   `pyserial` library
-   A Linux or macOS environment (for pseudo-terminal support)

### Installation

1.  **Clone the repository:**
    ```sh
    git clone <your-repo-url>
    cd enocean-simulator
    ```

## Usage

The simulation runs in two parts. You'll need two separate terminal windows.

### Terminal 1: Run the Simulator Sender

The main script starts the data generation process.

```sh
python main.py
```

Upon starting, it will print the name of the virtual serial port it has created. **Take note of this port name.**

**Example Output:**
```
============================================================
EnOcean Gateway Simulator - Complete 82 Devices
============================================================
[SimulatorManager] Starting EnOcean Gateway Simulator...
[GatewaySender] Started on /dev/ttys008
[DEBUG] DeviceManager devices before start: {}
[Main] Adding 82 devices to simulator...
============================================================
[Main] Processing 82 devices...
[Main] ✓ TempSensor (A5-02-01) -> ID: 789abc30
...
[Main] ✓ VLDPeopleCounter (D2-06-03) -> ID: 789abce7
============================================================
[Main] Device Summary: 82 added successfully, 0 failed
[Main] Simulation started with 82 devices
[Main] Press Ctrl+C to stop the simulation
============================================================
```

### Terminal 2: Run the Gateway Receiver (or Your App)

To see the data being generated, you can run the provided `gateway_receiver.py` as a standalone script. **You will need to slightly modify it to be runnable and pass it the port name from Terminal 1.**

*(Note: For a fully integrated experience, you could modify `main.py` or `simulator_manager.py` to launch the receiver in a separate process or thread).*

Assuming a runnable receiver script `run_receiver.py`:
```sh
# Replace /dev/ttys008 with the port name from the sender's output
python run_receiver.py --port /dev/ttys008
```

The receiver will start processing telegrams and creating log files in the `logs/` directory.

### Analyzing the Data

After running the simulator and receiver for a while, stop them (Ctrl+C). You can then use the `log_analyzer.py` tool to inspect the captured data.

```sh
# Analyze the most recent session
python tools/log_analyzer.py

# List all captured sessions
python tools/log_analyzer.py --list

# Generate a full report for a specific session
python tools/log_analyzer.py --session 20231027_103000 --report

# Show the last 15 raw telegrams from the latest session
python tools/log_analyzer.py --raw 15
```

## Project Structure

```
.
├── main.py                   # Main entry point to run the simulator sender.
├── enocean_simulator/
│   ├── devices/
│   │   ├── data_generator.py # Generates realistic data for each EEP type.
│   │   └── virtual_device.py # Class representing a single virtual device.
│   ├── gateway/
│   │   ├── device_manager.py # Manages all virtual devices.
│   │   ├── gateway_receiver.py # Reads, decodes, and logs data from the PTY.
│   │   └── gateway_sender.py # Creates PTY and sends telegrams.
│   ├── protocol/
│   │   ├── decoder.py        # Decodes raw telegram payloads into JSON.
│   │   ├── enums.py          # Enums for RORG and EEP types.
│   │   └── esp3.py           # Handles ESP3 protocol framing and checksums.
│   └── simulator_manager.py  # Orchestrates the sender and receiver components.
├── tools/
│   └── log_analyzer.py       # CLI tool to analyze captured log files.
└── logs/                       # (Created at runtime) Directory for all log outputs.
```
