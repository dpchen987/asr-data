from sys import argv
from video_speech_extracter import extract_align
from cut_audio import cut
import textwrap
import os
import datetime


PER_COUNT = 256
DEPTH = 2
AUDIO_FORMAT = 'opus'


def gen_subdirs(hashnum, per_count, depth):
    # 由于hashnumber最大不会超过2**64，所以一定小于20位。
    # 那么首先在hashnumber前添加0使其变为长度为20的string，然后根据count把string切成等长的sub-string。
    # 使用levels作为除数，用substring/levels得到的余数作为每层的文件命名
    # levels: 除数
    # count: 文件的层数

    digit = hashnum.zfill(20)                       # 将hashnumber变成长度为20的string
    cut_len = 20 // depth 
    if 20 % depth != 0:
        cut_len += 1
    parts = [digit[i:i+cut_len] for i in range(0, 20, cut_len)]
    print(parts)
    subdirs = []
    sub_name_len = len(str(per_count))
    for i in parts:
        subdir = int(i) % per_count
        subdirs.append(f'{subdir:0{sub_name_len}d}')
    return subdirs


def process(video_path, audio_root):
    hashnum = video_path.split('/')[-1].replace('.mp4', '')
    subdirs = gen_subdirs(hashnum, PER_COUNT, DEPTH)
    save_dir = os.path.join(audio_root, *subdirs, hashnum)
    print('save_dir:', save_dir)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        timeline = extract_align(video_path, save_dir)
    else:
        audio_path = f'{save_dir}/{hashnum}.{AUDIO_FORMAT}'
        if not os.path.exists(audio_path):
            timeline = extract_align(video_path, save_dir)
        else:
            timeline = None
            print('done: ', video_path)

    if timeline:
        audio_path = f'{save_dir}/{hashnum}.{AUDIO_FORMAT}'
        cut(audio_path, timeline)
        print('done: ', video_path)


def main():
    myid = int(argv[1])
    total = int(argv[2])
    paths = []
    _dir = '/aidata/video'
    audio_root = '/aidata/audio/private'
    time_threshold = datetime.datetime.now() - datetime.timedelta(minutes=10)
    for root, dirs, files in os.walk(_dir):
        for f in files:
            path = os.path.join(root, f)
            filetime = datetime.fromtimestamp(os.path.getmtime(path))
            if filetime < time_threshold:
                paths.append(path)

    for path in paths:
        print('path: ', path, '\n')
        hashnum = video_path.split('/')[-1].replace('.mp4', '')
        if not hashnum.isdigit():
            print('invalid hashnum: ', hashnum, '\n')
            continue 
        ihash = int(hashnum)
        if ihash % total != myid:
            continue 
        process(path, audio_root)
        
if __name__ == '__main__':
    main()
