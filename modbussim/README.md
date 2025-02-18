## Modbus Master and Slave Simulator Implementation
This project provides an implementation for modbus master and slave, and a docker-compose version.

## Required Libraries

You can test the implementation either via mannuall installation.

### Manual installation with VENV
```
python -m venv .venv/
pip install pymodbus==3.7.4
pip install pytest==8.3.4
pip install flask==2.1.2
pip install werkzeug==2.3.7
python modbus_server/main.py
```

```
python client/client.py
```

## Docker Compose (Quick Start)
Assuming that you have docker and docker compose at your development environment, then you can simply execute

`docker-compose up --build`

The interaction server/master and slave/client will be seen on the terminal.
