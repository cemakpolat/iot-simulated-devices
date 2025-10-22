import random

class BaseSensor:
    """Base class for all sensors."""
    def read(self):
        raise NotImplementedError

class TempSensor(BaseSensor):
    """Simulates a temperature sensor."""
    def __init__(self):
        self.last_reading = 22.0
    
    def read(self):
        # 5% chance of an anomaly
        is_anomaly = random.random() < 0.05
        if is_anomaly:
            reading = random.uniform(35, 45)
        else:
            # Gradual drift for normal readings
            drift = random.uniform(-0.5, 0.5)
            reading = self.last_reading + drift
            reading = max(18.0, min(30.0, reading)) # Clamp to a realistic normal range
        
        self.last_reading = reading
        return round(reading, 2)

class HumiditySensor(BaseSensor):
    """Simulates a humidity sensor."""
    def __init__(self):
        self.last_reading = 50.0

    def read(self):
        # 7% chance of an anomaly
        is_anomaly = random.random() < 0.07
        if is_anomaly:
            # Anomalies are very high or very low humidity
            reading = random.choice([random.uniform(10, 25), random.uniform(80, 95)])
        else:
            drift = random.uniform(-1.0, 1.0)
            reading = self.last_reading + drift
            reading = max(40.0, min(60.0, reading)) # Clamp to normal range
            
        self.last_reading = reading
        return round(reading, 2)