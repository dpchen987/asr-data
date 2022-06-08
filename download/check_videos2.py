from ezmysql import ConnectionSync
import os

db = ConnectionSync(
    host='localhost',
    database='asr_data',
    user='ahc_ai',
    password='yjKF@Ai_123',
    port=3306
)

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