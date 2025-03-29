class ESPHomeController:

    def __init__(self, hass, controller_data):
        self.hass = hass
        self._controller_data = controller_data

    async def send(self, command):
        """Send a command."""
        service_data = {"code": command}
        await self.hass.services.async_call(
            "esphome", self._controller_data, service_data
        )
