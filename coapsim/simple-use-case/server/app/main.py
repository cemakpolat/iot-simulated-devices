import asyncio
from config import Config
from client import ThermostatCoAPClient
from service import ThermostatControlService

async def main():
    config = Config()
    client = ThermostatCoAPClient(config.DEVICE_HOST, config.DEVICE_PORT)
    await client.setup()  
    service = ThermostatControlService()

    while True:
        temperature = await client.get_temperature()
        if temperature is not None:
            action = service.evaluate_and_act(temperature)
            await client.set_hvac_mode(action)
        await asyncio.sleep(config.POLL_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())