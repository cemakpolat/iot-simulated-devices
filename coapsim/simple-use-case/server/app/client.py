# import aiocoap
# import asyncio

# class ThermostatCoAPClient:
#     def __init__(self, host, port):
#         self.host = host
#         self.port = port

#     async def get_temperature(self):
#         uri = f"coap://{self.host}:{self.port}/temperature"
#         protocol = await aiocoap.Context.create_client_context()
#         request = aiocoap.Message(code=aiocoap.GET, uri=uri)
#         try:
#             response = await protocol.request(request).response
#             return float(response.payload.decode())
#         except Exception as e:
#             print(f"Error fetching temperature: {e}")
#             return None

#     async def set_hvac_mode(self, mode):
#         uri = f"coap://{self.host}:{self.port}/control"
#         protocol = await aiocoap.Context.create_client_context()
#         request = aiocoap.Message(code=aiocoap.POST, uri=uri, payload=mode.encode())
#         try:
#             response = await protocol.request(request).response
#             print(f"Command result: {response.payload.decode()}")
#         except Exception as e:
#             print(f"Error sending command: {e}")

import aiocoap
import asyncio

class ThermostatCoAPClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.protocol = None

    async def setup(self):
        self.protocol = await aiocoap.Context.create_client_context()

    async def get_temperature(self):
        uri = f"coap://{self.host}:{self.port}/temperature"
        request = aiocoap.Message(code=aiocoap.GET, uri=uri)
        try:
            response = await self.protocol.request(request).response
            return float(response.payload.decode())
        except Exception as e:
            print(f"Error fetching temperature: {e}")
            return None

    async def set_hvac_mode(self, mode):
        uri = f"coap://{self.host}:{self.port}/control"
        request = aiocoap.Message(code=aiocoap.POST, uri=uri, payload=mode.encode())
        try:
            response = await self.protocol.request(request).response
            print(f"Command result: {response.payload.decode()}")
        except Exception as e:
            print(f"Error sending command: {e}")
