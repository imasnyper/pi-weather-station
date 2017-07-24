from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import os.path


def do_auth():
	gauth = GoogleAuth()
	gauth.CommandLineAuth()
	drive = GoogleDrive(gauth)

	return drive

def upload_file(drive, path):
	head, title = os.path.split(path)
	f = drive.CreateFile({'title': title})
	f.SetContentFile(path)
	f.Upload()
	print('Title: {}, id: {}'.format(f['title'], f['id']))
	return f

if __name__ == '__main__':
	drive = do_auth()
	pic_folder = '/home/pi/Dev/weather_station/pics/'
	path = os.path.join(pic_folder, 'image-10-07-17 12:48:48.jpg')
	upload_file(drive, path)
