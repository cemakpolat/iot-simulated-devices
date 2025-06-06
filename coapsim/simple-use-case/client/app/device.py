import asyncio
from aiocoap import Context
from aiocoap.resource import Site
from resources.temperature import TemperatureResource
from resources.status import StatusResource
from resources.control import ControlResource
from config import Config

class ThermostatDevice:
    def __init__(self):
        self.config = Config()
        self.root = Site()

    def register_resources(self):
        self.root.add_resource(['temperature'], TemperatureResource())
        self.root.add_resource(['status'], StatusResource())
        self.root.add_resource(['control'], ControlResource())

    async def start(self):
        print(f"Starting CoAP server at coap://{self.config.HOST}:{self.config.PORT}")
        self.register_resources()
        await Context.create_server_context(self.root, bind=(self.config.HOST, self.config.PORT))
        await asyncio.sleep(3600 * 24)  # Run for 24 hours