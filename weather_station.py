import time
import datetime
import os
import os.path
import pickle
import argparse
import os
import os.path
import random
from pprint import pprint
import urllib.request
import json

import pytz
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

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
        self.path = os.path.join('/home/pi/Dev/pi-weather-station/pics/', 
            self.filename)

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


def upload_reading(unposted, debug, **kwargs):
    payload = {
        "temperature": kwargs['temp'],
        "humidity": kwargs['humidity'],
        "pressure": kwargs['pressure'],
        "date_time": kwargs['time'].strftime("%Y-%m-%dT%H:%M:%S")
    }

    if debug:
        upload_site = 'http://127.0.0.1:8000/api/add_reading'
    else:
        upload_site = 'http://wasaweather.com/api/add_reading'

    try:
        r = requests.post(upload_site, 
            data=payload)
        print(r)
        # for payload in unposted:
        #     r = requests.post(upload_site, 
        #         data=payload)
        #     if r.status_code == 201:
        #         unposted.remove(r)
    except requests.exceptions.ConnectionError:
        print("Connection to site could not be made."
            " Storing readings to upload next time")
        unposted.append(payload)


def upload_photo(picture_file):
    """Uploads a photo to website with http request
    Returns 201 if succesful, or the picture file if the upload fails
    """
    print("Picture size: " + str(os.stat(picture_file).st_size))
    upload_site = 'http://wasaweather.com/api/add_photo'
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
            upload_site, 
            headers={
                "Content-Type": multipart_data.content_type,
            },
            data=multipart_data,
        )
        print(r.headers["Content-Length"])
        # pprint(r.text)
        if r.status_code == 201:
            print(r.status_code)
            os.remove(picture_file)
            return r.status_code
        else:
            print(r.status_code)
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
    loop_wait = 60 * 1
    
    PICTURE_WAIT_MINUTES = 60

    unposted = []
    unposted_photos = []

    last_sun_picture = None

    if not debug:
        windsor = Location(
            ('Windsor', 'Ontario', 
            42.3149, -83.0364, 
            'Canada/Eastern', 190))

        tobermory = Location(
            ('Tobermory', 'Ontario',
            45.2534, -81.6645,
            'Canada/Eastern', 180))
        
        t_h_sensor = DHT22()
        # t_p_sensor = BMP280()
        camera = Camera()

        # chip_id, chip_version = t_p_sensor.read_id()

        #if not chip_id == 88:
        #    print("Error")
        #    print("Chip ID     : %d" % chip_id)
        #    print("Version     : %d" % chip_version)

    while True:
        # video_taken = False
        loop_time = datetime.datetime.now()
        loop_time_aware = pytz.timezone('Canada/Eastern').localize(loop_time)

        if not debug:
            dawn_time = tobermory.dawn()
            sunrise_time = tobermory.sunrise()
            dusk_time = tobermory.dusk()
            sunset_time = tobermory.sunset()

            try:
                humidity, dht_temp = t_h_sensor.read()
                print("DHT Humidity: {}\nDHT Temperature: {}".format(
                    humidity, dht_temp))

                #t_p_sensor.reg_check()
                #bmp_temp, pressure, altitude = t_p_sensor.read()
                #print("BMP Temperature: {}\nBMP Pressure: {}".format(
                #    bmp_temp, pressure
                #))
            except Exception as e:
                print("Error {} has occured, ignoring and going to next loop.".format(e))
                dht_temp, bmp_temp, humidity, pressure, altiture = None, None, None, None, None
                continue
        else:
            dht_temp, bmp_temp, humidity, pressure, altitude = generate_random()

        if humidity is not None and dht_temp is not None: #\
                #and bmp_temp is not None and pressure is not None:
            temp = dht_temp
            print(('{0:%d-%m-%y %X} - '
                   'Temperature = {1:0.1f}*\t'
                   'Humidity = {2:0.1f}%\t'
                   'mbar').format(loop_time, temp, humidity))

            upload_reading(unposted, debug, time=loop_time, temp=temp, humidity=humidity, 
                pressure=0)

        else:
            print('Failed to get reading.')

        stop_photo = urllib.request.urlopen("http://wasaweather.com/api/isstopped")
        data = stop_photo.read()
        data = json.loads(data)
        stopped = data['stopped']

        if CAMERA:
            picture_file = None
            # take picture every 3 minutes on the fifth minute, between the 
            # hours of dawn and sunrise, and dusk and sunset
            if dawn_time <= loop_time_aware <= sunrise_time \
                    + datetime.timedelta(minutes=20) \
                    or sunset_time <= loop_time_aware <= dusk_time:

                if not last_sun_picture or \
                        ((loop_time_aware - last_sun_picture).seconds / 60 >= 3):
                    picture_file = camera.take_picture(resolution=(2048, 1536))
                    last_sun_picture = loop_time_aware
            
            if sunrise_time <= loop_time_aware <= sunset_time:
                if loop_time.minute == 0:
                    picture_file = camera.take_picture(resolution=(2048, 1536))


            # for debugging
            # picture_file = camera.take_picture(resolution=(2048, 1536))

            if not debug and picture_file:
                print("Picture file created, attempting upload...")
                result = upload_photo(picture_file)
                # if type(result) == type(1):
                #     if len(unposted_photos) > 0:
                #         unposted_photos = upload_photos(unposted_photos)
                # if type(result) != type(1):
                #     unposted_photos.append(result)
            else:
                print("no picture file")


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
        from astral import Location
        
    main(debug=DEBUG, camera=CAMERA)
