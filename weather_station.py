import time
import datetime
import os
import os.path
import pickle
import argparse
import os
import os.path
import random

from astral import Astral
from picamera import PiCamera
from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

# from pydrive.auth import GoogleAuth
# from pydrive.drive import GoogleDrive
# from mydrive import G_Account

DATA_FILE = 'tempumidity.pickle'

GOOGLE_DRIVE_FOLDER_ID = '0B9LUnfJLTYXLZEItVXdnZFJwN3c'

CHART_FOLDER_ID = '0B9LUnfJLTYXLSGFCY3J5WU9PNTg'
CHART_ID = '0B9LUnfJLTYXLMzdvYjdsU29QU2M'
BOKEH_CHART = 'tempumidity.html'

CITY_NAME = 'Ottawa'


def pickle_data(data, data_file):
    with open(data_file, 'wb') as f:
        pickle.dump(data, f)


def unpickle_data(data_file):
    data_list = []
    with open(data_file, 'rb') as f:
        data = pickle.load(f)
        for d in data:
            data_list.append(d)

    return data_list


def bokeh_plot(data_list):
    output_file(BOKEH_CHART, title='Temp and Humidity at the House')

    date_times = [d[0] for d in data_list]
    temps = [d[1] for d in data_list]
    humidities = [d[2] for d in data_list]
    pressures = [d[3] for d in data_list]

    sp1 = figure(
        width=800,
        height=250,
        x_axis_type='datetime',
        title='Temperature',
        y_axis_label='Degrees Celcius'
    )
    sp1.line(date_times, temps, color='red')

    sp2 = figure(
        width=800,
        height=250,
        x_range=sp1.x_range,
        x_axis_type='datetime',
        title='Humidity',
        x_axis_label='Date/Time',
        y_axis_label='Percent',
    )
    sp2.line(date_times, humidities, color='darkblue')

    sp3 = figure(
        width=800,
        height=250,
        x_range=sp1.x_range,
        x_axis_type='datetime',
        title='Pressure',
        x_axis_label='Date/Time',
        y_axis_label='mbar',
    )
    sp3.line(date_times, pressures, color='purple')

    p = column(children=[sp1, sp2, sp3], sizing_mode="stretch_both")

    save(p)


class Camera:
    def __init__(self):
        self.camera = PiCamera()

    def take_picture(self, resolution=(3280, 2464), framerate=15):
        print('Taking picture...')

        self.camera.resolution = resolution
        self.framerate = framerate
        self.camera.vflip = True
        self.camera.hflip = True
        self.filename = 'image-{}.jpeg'.format(
            datetime.datetime.now().strftime('%d-%m-%y %X'))
        self.path = os.path.join('/home/pi/Dev/pi-weather-station/pics/', self.filename)

        self.camera.start_preview()

        time.sleep(3)

        self.camera.capture(self.path)
        self.camera.stop_preview()

        return self.path

    def take_video(self, resolution=(1920, 1080), framerate=30, length=10):
        print('Taking video...')

        self.camera.resolution = resolution
        self.camera.framerate = framerate
        self.camera.vflip = True
        self.camera.hflip = True

        self.camera.start_preview()

        time.sleep(3)

        self.camera.start_recording(('/home/pi/Dev/weather_station/videos/'
                                     'video-{}.h264').format(
                                         datetime.datetime.now().strftime(
                                             '%d-%m-%y %X')))
        self.camera.wait_recording(length)
        self.camera.stop_recording()
        self.camera.stop_preview()

        return length


def generate_random():
    dht_temp = random.uniform(-20.0, 35.0)
    bmp_temp = random.uniform(-20.0, 35.0)
    humidity = random.uniform(0.0, 100.0)
    pressure = random.uniform(950.0, 1100.0)
    altitude = random.uniform(0.0, 100.0)

    return dht_temp, bmp_temp, humidity, pressure, altitude


def main(debug=False, camera=False):
    # g_account = G_Account()

    timezone = datetime.timezone(-datetime.timedelta(hours=5))

    a = Astral()

    city = a[CITY_NAME]

    temp_pictures = []

    loop_wait = 60 * 1

    unposted = []
    unposted _photos = []

    try:
        l = unpickle_data(DATA_FILE)
    except FileNotFoundError:
        l = []

    if not DEBUG:
        t_h_sensor = DHT22()
        t_p_sensor = BMP280()
        camera = Camera()

        chip_id, chip_version = t_p_sensor.read_id()

        if not chip_id == 88:
            print("Error")
            print("Chip ID     : %d" % chip_id)
            print("Version     : %d" % chip_version)

    while True:
        # video_taken = False
        loop_time = datetime.datetime.now()
        loop_time_tz = datetime.datetime.now(tz=timezone)

        sun = city.sun(date=loop_time, local=True)

        if not DEBUG:
            humidity, dht_temp = t_h_sensor.read()
            print("DHT Humidity: {}\nDHT Temperature: {}".format(
                humidity, dht_temp))

            t_p_sensor.reg_check()
            bmp_temp, pressure, altitude = t_p_sensor.read()
            print("BMP Temperature: {}\nBMP Pressure: {}".format(
                bmp_temp, pressure
            ))
        else:
            dht_temp, bmp_temp, humidity, pressure, altitude = generate_random()

        if humidity is not None and dht_temp is not None and bmp_temp is not None and pressure is not None:
            temp = (dht_temp + bmp_temp) / 2
            print(('{0:%d-%m-%y %X} - '
                   'Temperature = {1:0.1f}*\tHumidity = {2:0.1f}%\tPressure = {3:0.2f} '
                   'mbar').format(
                       loop_time, temp, humidity, pressure, altitude))

            tup = (loop_time, temp, humidity, pressure)

            l.append(tup)

            bokeh_plot(l)

            pickle_data(l, DATA_FILE)

            payload = {
                "temperature": temp,
                "humidity": humidity,
                "pressure": pressure,
                "date_time": loop_time.strftime("%Y-%m-%dT%H:%M:%S")
            }

            try:
                r = requests.post('https://cottagevane.herokuapp.com/api/add_reading', data=payload)
                print(r)
                for payload in unposted:
                    r = requests.post('https://cottagevane.herokuapp/api/add_reading', data=payload)
                    print(r)
            except requests.exceptions.ConnectionError:
                print("Connection to site could not be made. Storing readings to upload next time")
                unposted.append(payload)
        else:
            print('Failed to get reading.')

        time_offset = datetime.timedelta(minutes=29)

        if CAMERA:
            # take picture every 5 minutes on the fifth minute, between the hours of dusk and dawn.
            if sun['dawn'] + time_offset <= loop_time_tz <= sun['dusk'] + time_offset:
                if loop_time.minute % 5 == 0:
                    picture_file = camera.take_picture()

                    try:
                        multipart_data = MultipartEncoder(
                            fields={
                                "data": (
                                    picture_file,
                                    open(picture_file, "rb"),
                                    "image/jpeg"
                                )
                            }
                        )
                        r = requests.post(
                            'https://cottagevane.herokuapp.com/api/add_photo', 
                            headers={
                                "Content-Type": multipart_data.content_type,
                            },
                            data=multipart_data,
                        )
                        print(r)
                        for multipart_data in unposted_photos:
                            r = requests.post(
                                'https://cottagevane.herokuapp.com/api/add_photo', 
                                headers={
                                    "Content-Type": multipart_data.content_type,
                                },
                                data=multipart_data,
                            )
                            print(r)
                    except requests.exceptions.ConnectionError:
                        print("Connection to site could not be made. Storing readings to upload next time")
                        unposted_photos.append(multipart_data)

        now = datetime.datetime.now()

        time_taken = now - loop_time
        print('Loop took {} seconds.'.format(time_taken.seconds))
        print('Sleeping {} seconds...'.format(loop_wait - now.second))
        time.sleep(loop_wait - now.second)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", help="turn debug on", action="store_true")
    parser.add_argument("--camera", help="turn camera on", action="store_true")
    args = parser.parse_args()

    DEBUG = args.debug
    CAMERA = args.camera

    if not DEBUG:
        from picamera import PiCamera
        from sensors import DHT22, BMP280
        
    main(debug=DEBUG, camera=CAMERA)
