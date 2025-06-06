import numpy as np
from sklearn.ensemble import IsolationForest

class ThermostatModel:
    def __init__(self):
        X_train = np.random.uniform(20, 25, size=(200, 1))
        self.model = IsolationForest(contamination=0.05)
        self.model.fit(X_train)

    def should_turn_on(self, temp):
        prediction = self.model.predict([[temp]])
        return prediction[0] == -1  # Turn on if anomaly detected