from sqlalchemy import create_engine
import pandas as pd
import json
from urllib import parse
from sqlalchemy.dialects import mysql

def import_db(res_li, db):
    user = 'ahc_ai'
    pwd = parse.quote_plus('yjKF@Ai_123')
    host = '127.0.0.1'
    url = f"mysql+pymysql://{user}:{pwd}@{host}:3306/asr_data?charset=utf8"

    conn = create_engine(url, echo=False, encoding="utf-8")
    with open(res_li, 'r') as f:
        data = json.load(f)

    video = pd.DataFrame(data).head(10000)
    video = video.astype({'url_hash': 'str'})
    video.to_sql(db, con=conn, if_exists='append', index=False)


# res_list = 'CCTV_episode.json'
# import_db(res_list, 'Hub')
res_list = 'CCTV_video_list.json'
import_db(res_list, 'Video')