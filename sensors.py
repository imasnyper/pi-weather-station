import board
import busio
import adafruit_bmp280
import Adafruit_DHT


class BMP280:
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.sensor = adafruit_bmp280.Adafruit_BMP280_I2C(self.i2c)
        self.sea_level_pressure = None

    def read_temperature(self):
        return self.sensor.temperature

    def read_pressure(self):
        return self.sensor.pressure

    def read_altitude(self):
        if self.sea_level_pressure:
            return self.sensor.altitude
        else:
            self.sensor.sea_level_pressure = self.sea_level_pressure
            return self.sensor.altitude


class DHT22:
    """
    Class to contain sensor pin information and methods to read the sensor.
    """

    def __init__(self, pin=None):
        self.sensor = Adafruit_DHT.DHT22
        self.pin = pin if pin else 18

    def read(self):
        humidity, temperature = Adafruit_DHT.read_retry(self.sensor, self.pin)

        return humidity, temperature
