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

# 按照一个CCTV一个腾讯的方式获取视频
# sql1 = "select video_path, url_hash, url from Video where episode_name != '金牌调节' and episode_name != '爱情保卫战'"
# sql2 = "select video_path, url_hash, url from Video where episode_name = '金牌调节' or episode_name = '爱情保卫战'"

# 按顺序获取视频（检查是否全部视频都被获取）
sql = "select video_path, url_hash, url from Video"


# ds_cctv = db.query(sql1)
# ds_tencent = db.query(sql2)
ds = db.query(sql)


# 视频下载
def download(i):
    # i：sql select一行的值
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

for i in range(len(ds)):
    # 从后往前按照一个CCTV一个腾讯的方式下载，若想按照从前往后的顺序，将-（i+1）改成i即可
    # info = ds_cctv[-(i+1)]
    # download(info)

    # if i < len(ds_tencent):
    #     info = ds_tencent[-(i+1)]
    #     download(info)

    # 按顺序下载
    info = ds[i]
    download(info)


# 检查有哪些视频没有成功下载，将没有成功下载的视频从sql数据库中删除
paths = []
_dir = '/aidata/video/电视剧2'
for root, dirs, files in os.walk(_dir):
    for f in files:
        path = os.path.join(root, f)
        paths.append(path)
import re
# r = re.compile(".*\.download")
r = re.compile(".*\[.*\].*")
newlist = list(filter(r.match, paths)) # Read Note below
for i in newlist:
    print(i)
    os.system(f"rm {i}")

import os
sql = 'select video_path from Video'
ds = db.query(sql)

for i in ds:
    path = i['video_path']
    if ('电视剧2' in path) and (not os.path.exists(path)):
        delete_sql = f'DELETE FROM Video WHERE video_path="{path}";'
        print(delete_sql)
        db.query(delete_sql)
        print(path)




