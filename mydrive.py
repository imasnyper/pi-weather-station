from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.files import ApiRequestError

from urllib.error import HttpError

import os
import os.path

import time
import datetime

import pickle
import csv

import random

def create_dummy_data():
    temps = [random.randint(0, 35) for _ in range(10)]
    humidities = [random.uniform(0.0, 99.9) for _ in range(10)]

    return list(zip(temps, humidities))

def export_csv(file, data):
    print(data)
    with open(file, newline='') as f:
        writer = csv.writer(f)
        for d in data:
            writer.writerow(['{}'.format(d[0])])
            writer.writerow(['{}'.format(d[1])])

def import_csv(file):
    data = []
    with open(file, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            data.append(row)

    return data


def pickle_data(file, data):
    with open(file, 'wb') as f:
        pickle.dump(data, f)

def unpickle_data(file):
    with open(file, 'rb') as f:
        data = pickle.load(f)

    return data


class G_Account():

    def __init__(self):
        self.gauth = GoogleAuth('settings.yaml')
        self.gauth.CommandLineAuth()
        self.drive = GoogleDrive(self.gauth)

    def upload_file(self, local_path, parent_folder='', f_id=''):
        head, title = os.path.split(local_path)
        f_metadata = {'title': title}

        if parent_folder:
            f_metadata['parents'] = [{'id': parent_folder}]
        if f_id:
            f_metadata['id'] = f_id

        f = self.drive.CreateFile(f_metadata)
        f.SetContentFile(local_path)
        try:
            f.Upload()
        except HTTPError as e:
            print('Server error {}.\nRefreshing Google auth token and retyring.'.format(e.code))
            self.gauth.Refresh()
            f.Upload()

        return f

    def get_file_metadata(self, file_id):
        f = self.drive.CreateFile({'id': file_id})

        try:
            f.FetchMetadata()
            metadata = f.metadata
        except HTTPError as e:
            print("Server error {}. \nRefreshing Google auth token and retrying.".format(e.code))
            self.gauth.Refresh()
            f.FetchMetadata()
            metadata = f.metadata

        return metadata


if __name__ == "__main__":
    data = create_dummy_data()
    export_csv('test.csv', data)
    new_data = import_csv('test.csv')
    for d in new_data:
        print(d)

    ##g_account = G_Account()
    ##f_id = g_account.upload_file('test.txt')
    ##start_time = datetime.datetime.now()
    ##while True:
    ##    t = datetime.datetime.now()
    ##    if t.minute % 5 == 0:
    ##        print(t)
    ##        print('Time since started: {}'.format(t - start_time))
    ##        metadata = g_account.get_file_metadata(f_id)
    ##        print(metadata['title'])
    ##
    ##    time.sleep(60)
