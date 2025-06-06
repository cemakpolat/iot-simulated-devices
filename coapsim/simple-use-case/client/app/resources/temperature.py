import random
from aiocoap import Message
from aiocoap.resource import Resource


class TemperatureResource(Resource):
    def __init__(self):
        super().__init__()
        self.temperature = self.generate_temperature()

    def generate_temperature(self):
        base = random.uniform(20, 25)
        if random.random() < 0.05:
            base = random.uniform(30, 40)
        return round(base, 2)

    async def render_get(self, request):
        self.temperature = self.generate_temperature()
        print("📥 GET request received at /temperature")

        payload = f"{self.temperature}".encode('utf-8')
        return Message(payload=payload)