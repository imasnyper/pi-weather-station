import time
import datetime

import pickle

from picamera import PiCamera

from bokeh.plotting import figure, output_file, save
from bokeh.models.ranges import DataRange1d
from bokeh.models import LinearAxis
from bokeh.layouts import column
from bokeh.io import export_png

import sqlite3

from sensors import DHT22, BMP280

# from pydrive.auth import GoogleAuth
# from pydrive.drive import GoogleDrive
from mydrive import G_Account

import os
import os.path

save_file = 'tempumidity.pickle'

GOOGLE_DRIVE_FOLDER_ID = '0B9LUnfJLTYXLZEItVXdnZFJwN3c'
CHART_FOLDER_ID = '0B9LUnfJLTYXLSGFCY3J5WU9PNTg'

def pickle_data(data, save_file):
    with open(save_file, 'wb') as f:
        pickle.dump(l, f)

def unpickle_data(data_list, save_file):
    with open(save_file, 'rb') as f:
        data = pickle.load(f)
        for d in data:
            data_list.append(d)

    return data_list

def bokeh_plot(data_list, g_drive_upload=False, g_account=None, g_drive_file_id=None):
    output_file('tempumidity.html', title='Temp and Humidity at the House')

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

    # p.extra_y_ranges = {"hum": DataRange1d(start=0, end=100)}
    # p.line(date_times, humidities, color='darkblue', y_range_name='hum', legend='Humidity')
    # p.add_layout(LinearAxis(y_range_name='hum'), 'left')

    p = column(children=[sp1, sp2, sp3], sizing_mode="stretch_both")

    # p.title.text = 'Temp and Humidity at the House'
    # p.legend.location = 'top_left'
    # p.xaxis.axis_label = 'Date'
    # p.yaxis.axis_label = 'Temperature'
    # p.y_range = y_ran

    save(p)
    # png_file = export_png(p, filename='tempumidity.png')
    if g_drive_upload:
        if g_drive_file_id:
            drive_file = g_account.upload_file(
                'tempumidity.html', parent_folder=CHART_FOLDER_ID, f_id=g_drive_file_id)
        else:
            drive_file = g_account.upload_file('tempumidity.html', parent_folder=CHART_FOLDER_ID)
        return drive_file['id']
    else:
        return None

# def do_auth():
# 	gauth = GoogleAuth('settings.yaml')
# 	gauth.CommandLineAuth()
# 	drive = GoogleDrive(gauth)
#
# 	return gauth, drive
#
# def google_drive_upload(drive, g_auth, filename, parent_folder='', id=None):
#     head, title = os.path.split(filename)
#     f_metadata = {'title': title}
#     if parent_folder:
#         f_metadata['parents'] = [{'id': parent_folder}]
#     if id:
#         f_metadata['id'] = id
#
#     f = drive.CreateFile(f_metadata)
#     f.SetContentFile(filename)
#     try:
#         f.Upload()
#     except pydrive.files.ApiRequestError:
#         g_auth.Refresh()
#         f.Upload()
#
#     return f


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
        self.path = os.path.join('/home/pi/Dev/weather_station/pics/', self.filename)
        # self.camera.iso = 100
        # time.sleep(2)
        # self.camera.shutter_speed = self.camera.exposure_speed
        # self.camera.exposure_mode = 'off'
        # g = self.camera.awb_gains
        # self.camera.awb_mode = 'off'
        # self.camera.awb_gains = g

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
        # self.camera.iso = 100
        # time.sleep(2)
        # self.camera.shutter_speed = self.camera.exposure_speed
        # self.camera.exposure_mode = 'off'
        # g = self.camera.awb_gains
        # self.camera.awb_mode = 'off'
        # self.camera.awb_gains = g

        self.camera.start_preview()

        time.sleep(3)

        self.camera.start_recording('/home/pi/Dev/weather_station/videos/video-{}.h264'.format(datetime.datetime.now().strftime('%d-%m-%y %X')))
        self.camera.wait_recording(length)
        self.camera.stop_recording()
        self.camera.stop_preview()

        return length

def main():
    # gauth, drive = do_auth()
    g_account = G_Account()
    drive_plot_file_id = None

    try:
        l = unpickle_data([], save_file)
    except FileNotFoundError:
        l = []
    t_h_sensor = DHT22()
    t_p_sensor = BMP280()
    camera = Camera()

    chip_id, chip_version = t_p_sensor.read_id()

    if not chip_id == 88:
        print("Error")
        print("Chip ID     : %d" % chip_id)
        print("Version     : %d" % chip_version)

    picture_path = camera.take_picture()
    g_account.upload_file(
        picture_path, parent_folder=GOOGLE_DRIVE_FOLDER_ID)
    os.remove(picture_path)

    # camera.take_video()

    old_picture_time = datetime.datetime.now()
    # old_video_time = old_picture_time
    picture_delay = datetime.timedelta(minutes=10)
    # video_delay = datetime.timedelta(hours=1)

    while True:
        # video_taken = False

        humidity, dht_temp = t_h_sensor.read()

        t_p_sensor.reg_check()
        bmp_temp, pressure, altitude = t_p_sensor.read()

        temp = (dht_temp + bmp_temp) / 2

        dt = datetime.datetime.now()

        if dt - old_picture_time > picture_delay:
            old_picture_time = dt
            try:
                camera.take_picture(g_drive_upload=True, g_account=g_account)
            except pydrive.files.ApiRequestError:
                camera.take_picture()

        # if dt - old_video_time > video_delay:
        #     old_video_time = dt
        #     video_length = camera.take_video()
        #     video_taken = True

        if humidity is not None and dht_temp is not None:
            print('{0} - Temp={1:0.1f}* Humidity={2:0.1f}% Pressure={3:0.2f} mbar'.format(dt, temp, humidity, pressure, altitude))

            tup = (dt, temp, humidity, pressure)

            l.append(tup)

            drive_plot_file_id = bokeh_plot(l, g_drive_upload=True, g_account=g_account, g_drive_file_id=drive_plot_file_id)

            with open(save_file, 'wb') as f:
                pickle.dump(l, f)

        else:
            print('Failed to get reading.')

        # if video_taken:
        #     if video_length > 60:
        #         continue
        #     else:
        #         time.sleep(60-video_length)
        # else:
        #     time.sleep(60)

        time.sleep(60)

if __name__ == '__main__':
    main()
