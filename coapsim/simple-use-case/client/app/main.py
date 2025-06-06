import asyncio
from device import ThermostatDevice

def main():
    device = ThermostatDevice()
    asyncio.run(device.start())

if __name__ == "__main__":
    main()