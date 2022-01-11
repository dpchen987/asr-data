import pandas as pd
from ezmysql import ConnectionSync
import os
import time

db = ConnectionSync(
    host='localhost',
    database='asr_data',
    user='ahc_ai',
    password='yjKF@Ai_123',
    port=3306
)
sql = 'select * from Video'
ds = pd.DataFrame(db.query(sql))

finish = 0
for i in range(len(ds)):
    row = ds.loc[i, :]
    path = '/aidata/video'

    if row['video_path'] != 'NaN':
        continue

    if row['episode_type'] == 0:
        path += ('/' + '电视剧' + '/' + row['episode_name'])
    else:
        path += ('/' + '综艺' + '/' + row['episode_name'] + '/' + str(row['year']))

    if not os.path.exists(path):
        os.makedirs(path)
    os.system(f"you-get -o {path} -O '{str(row['url_hash'])}' '{row['url']}'")

    path += '/' + str(row['url_hash']) + '.mp4'

    sql = f"update Video set video_path = '{path}' where id = {row['id']}"
    db.query(sql)

    finish += 1

    if finish % 10 == 0:
        print(f'finish {round(finish / len(ds) * 100, 2)}%')

    time.sleep(10)