from sys import argv
from video_speech_extracter import extract_align
from cut_audio import cut
import textwrap
import os

LEVEL = 256
COUNT = 2

def gen_path(hashnum, levels, count):
    # 由于hashnumber最大不会超过2**64，所以一定小于20位。
    # 那么首先在hashnumber前添加0使其变为长度为20的string，然后根据count把string切成等长的sub-string。
    # 使用levels作为除数，用substring/levels得到的余数作为每层的文件命名
    # levels: 除数
    # count: 文件的层数

    digit = hashnum.zfill(20)                       # 将hashnumber变成长度为20的string
    cut_len = 20 // count
    if 20%count != 0:
        cut_len += 1
    cut_digit = textwrap.wrap(digit, cut_len)       # 根据count切成登场的substring
    file_path = '/aidata/audio/private'
    # print(cut_digit)
    for i in cut_digit:
        sub_digit = int(i)
        level_digit = sub_digit % levels            # 每层的文件名
        file_path += '/' + str(level_digit).zfill(len(str(levels)))
    return file_path

paths = []
_dir = '/aidata/video'
for root, dirs, files in os.walk(_dir):
    for f in files:
        path = os.path.join(root, f)
        paths.append(path)

for path in paths:
    print('path: ', path, '\n')
    hashnum = path.split('/')[-1].replace('.mp4', '')
    file_path = gen_path(hashnum, LEVEL, COUNT)
    if not os.path.exists(file_path):
        os.makedirs(file_path)
        os.system(f"cp {path} {file_path}")

        vp = file_path + '/' + hashnum + '.mp4'
        print('file path: ', vp, '\n')
        timeline = extract_align(vp)
        audio_file = vp.replace('mp4', 'wav')
        cut(audio_file, timeline)

        os.system(f"rm {file_path}")
    else:
        print(path, file_path)
