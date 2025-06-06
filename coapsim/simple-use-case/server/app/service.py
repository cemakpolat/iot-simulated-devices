import json
from model import ThermostatModel

class ThermostatControlService:
    def __init__(self):
        self.model = ThermostatModel()

    def evaluate_and_act(self, temperature):
        if self.model.should_turn_on(temperature):
            print(f"Anomaly detected: {temperature}°C → Turning on HVAC")
            return "on"
        else:
            print(f"Normal reading: {temperature}°C → Keeping off")
            return "off"