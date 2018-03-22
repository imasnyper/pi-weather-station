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
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

# from pydrive.auth import GoogleAuth
# from pydrive.drive import GoogleDrive
# from mydrive import G_Account

DATA_FILE = 'tempumidity.pickle'

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


class Camera:
    def __init__(self):
        self.camera = PiCamera()

    def take_picture(self, resolution=(3280, 2464), framerate=15):
        print('Taking picture...')

        self.camera.resolution = resolution
        self.framerate = framerate
        self.camera.vflip = False
        self.camera.hflip = False
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

        self.camera.start_recording(('/home/pi/Dev/pi-weather-station/videos/'
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


def upload_photo(picture_file):
    try:
        multipart_data = MultipartEncoder(
            fields={
                "photo": (
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
        if r.status_code == 201:
            os.remove(picture_file)
            return r.status_code
        else:
            return picture_file

    except requests.exceptions.ConnectionError:
        print("Connection to site could not be made. Storing readings to upload next time")
        return picture_file


def upload_photos(picture_files):
    for picture in picture_files:
        result = upload_photo(picture)
        if type(result) != type(1):
            return picture_files

    return []


def round_time(dt=None, roundTo=60):
   """Round a datetime object to any time laps in seconds
   dt : datetime.datetime object, default now.
   roundTo : Closest number of seconds to round to, default 1 minute.
   Author: Thierry Husson 2012 - Use it as you want but don't blame me.
   """
   if dt == None : dt = datetime.datetime.now()
   seconds = (dt.replace(tzinfo=None) - dt.min).seconds
   rounding = (seconds+roundTo/2) // roundTo * roundTo
   return dt + datetime.timedelta(0,rounding-seconds,-dt.microsecond)


def main(debug=False, camera=False):
    # g_account = G_Account()

    timezone = datetime.timezone(-datetime.timedelta(hours=5))

    a = Astral()

    city = a[CITY_NAME]

    temp_pictures = []

    loop_wait = 60 * 1

    PICTURE_WAIT_MINUTES = 10


    unposted = []
    unposted_photos = []

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
        loop_time_tz_rounded = round_time(datetime.datetime.now(tz=timezone))

        sun = city.sun(date=loop_time, local=True)
        time_offset = datetime.timedelta(minutes=29)
        sunrise_time = round_time(sun['dawn'] + time_offset)
        sunset_time = round_time(sun['dusk'] + time_offset)

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

        if CAMERA:
            picture_file = None
            if sunrise_time == loop_time_tz_rounded or sunset_time == loop_time_tz_rounded:
                picture_file = camera.take_picture()
            # take picture every 5 minutes on the fifth minute, between the hours of dusk and dawn.
            if sunrise_time <= loop_time_tz_rounded <= sunset_time:
                if loop_time.minute % PICTURE_WAIT_MINUTES == 0:
                    picture_file = camera.take_picture()

            if not DEBUG and picture_file:
                result = upload_photo(picture_file)
                if type(result) == type(1):
                    if unposted_photos.length() > 0:
                        unposted_photos = upload_photos()
                if type(result) != type(1):
                    unposted_photos.append(result)


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
