from aiocoap import Message
from aiocoap.resource import Resource


class StatusResource(Resource):
    async def render_get(self, request):
        return Message(payload=b"OK")