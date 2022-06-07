import pandas as pd
from ezmysql import ConnectionSync
import os
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--start',type=int,default=0)

opt = parser.parse_args()

db = ConnectionSync(
    host='localhost',
    database='asr_data',
    user='ahc_ai',
    password='yjKF@Ai_123',
    port=3306
)
sql = f'select * from Video limit {opt.start},15000;'
ds = pd.DataFrame(db.query(sql))

finish = 0
for i in range(len(ds)):
    row = ds.loc[i, :]
    path = '/aidata/video'
    video_path = row['video_path']
    print(video_path)

    if not os.path.exists(video_path):

        if row['episode_type'] == 0:
            path += ('/' + '电视剧2' + '/' + row['episode_name'])
        else:
            path += ('/' + '综艺' + '/' + row['episode_name'] + '/' + str(row['year']))

        if not os.path.exists(path):
            os.makedirs(path)
        os.system(f"you-get -o {path} -O '{str(row['url_hash'])}' '{row['url']}'")

    finish += 1

    if finish % 100 == 0:
        print(f'finish {round(finish / len(ds) * 100, 2)}%')

    # time.sleep(10)