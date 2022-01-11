from ezmysql import ConnectionSync
import os

db = ConnectionSync(
    host='localhost',
    database='asr_data',
    user='ahc_ai',
    password='yjKF@Ai_123',
    port=3306
)
sql = 'select video_path, url_hash, url from Video'
ds = db.query(sql)

for i in ds:
    path = i['video_path']
    if path != 'NaN':
        if not os.path.exists(path):
            print(f"you-get -o {('/').join(path.split('/')[:-1])} -O '{str(i['url_hash'])}' '{i['url']}'")
            # print(f"you-get -o {('/').join(path.split('/')[:-1])} -o '{str(i['url_hash'])}' '{i['url']}'")
            os.system(f"you-get -o {('/').join(path.split('/')[:-1])} -O '{str(i['url_hash'])}' '{i['url']}'")
            # break