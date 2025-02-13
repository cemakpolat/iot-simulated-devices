# TCP Server-Client Example

This project demonstrates a TCP client-server connection for simulating telemetry data transmission. It is designed to simulate a TCP connection with generated data, eliminating the need for physical devices or external services.

## Features
- **TCP Server**: Listens for incoming client connections and logs received telemetry data.
- **TCP Client**: Periodically generates and sends telemetry data (temperature and humidity) to the server.
- **Docker Support**: Run the server and client in isolated containers using Docker Compose.
- **Customizable**: Easily modify data generation, server, and client behavior.
- **Scalable**: Run multiple clients simultaneously to simulate multiple devices.

---

## Quick Start with Docker Compose

### Prerequisites
- Docker and Docker Compose installed on your system.

### Build and Run Services
1. Navigate to the project directory containing the `docker-compose.yml` file.
2. Run the following command to build and start the services:

   ```bash
   docker-compose up --build
   ```

   This will start the server and client containers.

### Override Environment Variables
You can customize the behavior of the server and client using environment variables. For example, to specify a custom device name:

   ```bash
   DEVICE_NAME=custom_device_1234 docker-compose up --build
   ```

### Scale Client Instances
To simulate multiple devices, you can scale the number of client instances. For example, to run 3 clients:

   ```bash
   docker-compose up --scale client=3
   ```

### Stop All Services
To stop and remove all running containers, use:

   ```bash
   docker-compose down
   ```

---

## Mono Code (Development Environment)

The second part of the code is designed for development and testing without Docker. You can run the server and client directly on your local machine.

### How to Run
1. Ensure Python 3.9 or later is installed.
2. Navigate to the project directory.
3. Run the server:

   ```bash
   python server.py
   ```

4. In a separate terminal, run the client:

   ```bash
   python client.py
   ```

### Customization
- Modify the `generate_telemetry` function in `client.py` to change the data generation logic.
- Update the server's `handle_client` method in `server.py` to process incoming data differently.
- Add new features or functionality as needed.

---

## Project Structure
```
.
├── Dockerfile.client          # Dockerfile for the client
├── Dockerfile.server          # Dockerfile for the server
├── docker-compose.yml         # Docker Compose configuration
├── server.py                  # TCP server implementation
├── client.py                  # TCP client implementation
├── README.md                  # Project documentation
```

---

## Environment Variables
### Server
- `SERVER_HOST`: The host address the server binds to (default: `0.0.0.0`).
- `SERVER_PORT`: The port the server listens on (default: `50001`).

### Client
- `SERVER_HOST`: The host address of the server (default: `server`).
- `SERVER_PORT`: The port of the server (default: `50001`).
- `DEVICE_NAME`: The name of the device (default: `device_XXXX`, where `XXXX` is a random 4-digit number).

---

## Example Use Cases
- **IoT Simulation**: Simulate multiple IoT devices sending telemetry data to a central server.
- **Load Testing**: Test the server's ability to handle multiple client connections.
- **Development**: Experiment with TCP communication and data processing in a controlled environment.

---

## Troubleshooting
- **Connection Issues**: Ensure the server is running and the correct `SERVER_HOST` and `SERVER_PORT` are used.
- **Docker Errors**: Verify Docker and Docker Compose are installed and running correctly.
- **Logs**: Check the logs for errors or warnings. Use `docker-compose logs` for Docker-based deployments.

---

## Contributing
Feel free to contribute to this project by opening issues or submitting pull requests. Your feedback and improvements are welcome!

---

## License
This project is open-source and available under the [MIT License](LICENSE).
