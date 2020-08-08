"""
Runs on ESP8266
Read from temperature sensor and send to both oled display and remote socket

https://arduinomodules.info/ky-013-analog-temperature-sensor-module/
On my sensor, ground and vcc seem to be switched, which is apparently common
plugged into 3v3
"""
from machine import Pin, ADC, I2C
from time import sleep
from math import log
import ssd1306
import socket
import network

# pin constants
SCL = 5
SDA = 4

# oled setup
i2c = I2C(-1, scl=Pin(SCL), sda=Pin(SDA))
width, height = 64, 48
oled = ssd1306.SSD1306_I2C(width, height, i2c)


class Temperature:
    def __init__(self):
        # setup equation to convert resistance to temperature - steinhart-hart equation
        # steinhart-hart coefficients for thermistor
        # these coefficients are bunk, need to find correct values
        self.c1 = 0.001129148
        self.c2 = 0.000234125
        self.c3 = 0.0000000876741
        self.r1 = 10000  # value of R1 on the board?

        # get analog input
        self.analog = ADC(0)

        # populate
        self.read()

    def read(self):
        self.analog_value = self.analog.read()
        print(self.analog_value)

    def convert(self):
        # supposedly this is the steinhart-hart equation which will convert for us
        r2 = self.r1 * (1023.0 / self.analog_value - 1.0)                   # calculate resistance on thermistor
        logr2 = log(abs(r2))                                                # todo: remove abs
        TK = (1.0 / (self.c1 + self.c2 * logr2 + self.c3 * logr2 * logr2 * logr2))  # temperature in Kelvin
        TC = TK - 273.15                                                    # convert Kelvin to Celcius
        print(TC)
        TF = (TC * 9.0) / 5.0 + 32.0                                        # convert Celcius to Farenheit
        return {"K": TK, "C": TC, "F": TF}

    def output_oled(self, k, c, f):
        # output raw value
        oled.fill(0)
        oled.text(str(self.analog_value), 0, 30, 1)

        # output converted values
        # oled.fill(0)
        oled.text(str(int(k)) + " K", 0, 0, 1)
        oled.text(str(int(c)) + " C", 0, 10, 1)
        oled.text(str(int(f)) + " F", 0, 20, 1)

        oled.show()

    def update(self):
        self.read()
        # to human readable
        hr = self.convert()
        self.output_oled(hr["K"], hr["C"], hr["F"])
        return self.analog_value


class Network:
    def do_connect(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        if not self.wlan.isconnected():
            print('connecting to network...')
            self.wlan.connect('essid', 'password')
            while not self.wlan.isconnected():
                pass
        print('network config:', self.wlan.ifconfig())

    def __init__(self):
        # connect to wifi
        self.do_connect()

        # todo: separate this into own function
        # for socket connection
        self.host = "192.168.1.8"
        self.port = 65432
        self.sock = socket.socket()
        self.sock.connect((self.host, self.port))

    def send(self, msg):
        self.sock.send((str(msg) + "\n").encode())

    def close(self):
        self.sock.close()
        #self.sock.shutdown(socket.SHUT_RDWR)

t = Temperature()
n = Network()

while True:
    try:
        n.send(t.update())
    except OSError as e:
        # todo: make this error handling more meaningful
        print(e)
        print("Failed to send data over network")
        n.close()
        break
    sleep(1)
