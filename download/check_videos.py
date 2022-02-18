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
sql1 = "select video_path, url_hash, url from Video where episode_name != '金牌调节' and episode_name != '爱情保卫战'"
sql2 = "select video_path, url_hash, url from Video where episode_name = '金牌调节' or episode_name = '爱情保卫战'"

ds_cctv = db.query(sql1)
ds_tencent = db.query(sql2)

def download(i):
    path = i['video_path']
    if path != 'NaN':
        if not os.path.exists(path):
            dir = ('/').join(path.split('/')[:-1])
            if not os.path.exists(dir):
                os.makedirs(dir)
            print(f"you-get -o {('/').join(path.split('/')[:-1])} -O '{str(i['url_hash'])}' '{i['url']}'")
            # print(f"you-get -o {('/').join(path.split('/')[:-1])} -o '{str(i['url_hash'])}' '{i['url']}'")
            os.system(f"you-get -o {('/').join(path.split('/')[:-1])} -O '{str(i['url_hash'])}' '{i['url']}'")

    print('sleeping')
            # time.sleep(60)
            # break

for i in range(len(ds_cctv)):
    info = ds_cctv[-(i+1)]
    download(info)

    if i < len(ds_tencent):
        info = ds_tencent[-(i+1)]
        download(info)


# paths = []
# _dir = '/aidata/video'
# for root, dirs, files in os.walk(_dir):
#     for f in files:
#         path = os.path.join(root, f)
#         paths.append(path)
# import re
# # r = re.compile(".*\.download")
# r = re.compile(".*\[.*\].*")
# newlist = list(filter(r.match, paths)) # Read Note below
# for i in newlist:
#     os.system(f"rm {i}")
#
# import os
# sql = 'select video_path from Video'
# ds = db.query(sql)
#
# for i in ds:
#     path = i['video_path']
#     if not os.path.exists(path):
#         delete_sql = f'DELETE FROM Video WHERE video_path="{path}";'
#         print(delete_sql)
#         db.query(delete_sql)
#         print(path)




