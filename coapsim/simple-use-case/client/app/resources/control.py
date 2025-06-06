from aiocoap import Message
from aiocoap.resource import Resource


class ControlResource(Resource):
    def __init__(self):
        super().__init__()
        self.hvac_state = "off"

    async def render_post(self, request):
        command = request.payload.decode().strip().lower()
        if command in ["on", "off"]:
            self.hvac_state = command
            response = f"HVAC set to {command}"
        else:
            response = "Invalid command. Use 'on' or 'off'"
        return Message(payload=response.encode())