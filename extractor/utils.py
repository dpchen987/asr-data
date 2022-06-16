#!/usr/bin/env python3

import os
import re
import difflib
import farmhash


differ = difflib.SequenceMatcher(isjunk=lambda x: x == ' ')


def get_hashid(path, is_name_hash=True):
    name = path.split('/')[-1].split('.')[0]
    if is_name_hash:
        return int(name)
    hashid = farmhash.hash64(path)
    return hashid


def get_name(path):
    name = path.split('/')[-1].rsplit('.', maxsplit=1)[0]
    return name


def save_list(list_data, file_path):
    with open(file_path, 'w') as f:
        for t in list_data:
            z = [str(i) for i in t]
            s = "\t".join(z)
            line = f'{s}\n'
            f.write(line)


def is_float(t):
    return re.match(r'^[\d.]+$', t)


def read_list(file_path):
    items = []
    with open(file_path) as f:
        for line in f:
            zz = line.strip().split('\t')
            item = []
            for z in zz:
                if z.isdigit():
                    item.append(int(z))
                    continue
                if is_float(z):
                    item.append(float(z))
                    continue
                item.append(z)
            if len(zz) == 1:
                item.append('')
            items.append(item)
    return items


P_CHARS = re.compile(r'[^0-9a-zA-Z\u4E00-\u9FA5]+')


def text_normalize(text):
    return P_CHARS.sub('', text)


def calc_similary(t1, t2):
    differ.set_seq1(t1)
    differ.set_seq2(t2)
    return differ.ratio()


def get_audio(
        video_path, audio_path,
        channel=1, samplerate=48000, bitrate=32000):
    args = [
        f'-ac {channel}',
        f'-ar {samplerate}',
        # f'-ab {bitrate}',
        '-y',
    ]
    supported_format = {
        'wav': '-map_metadata -1 -fflags +bitexact -acodec pcm_s16le',
        'opus': ' -f wav - | opusenc - ',
        'mp3': '-acodec libmp3lame',
    }
    format = audio_path.split('.')[-1].lower()
    if format not in supported_format:
        raise ValueError(f'not supported audio format: {format}')
    args.append(supported_format[format])
    args = ' '.join(args)
    cmd = f'ffmpeg -i {video_path} {args} {audio_path}'
    print(cmd)
    os.system(cmd)


def gen_subdirs(hashid, per_count, depth):
    # 由于hashidber最大不会超过2**64，所以一定小于20位。
    # 那么首先在hashidber前添加0使其变为长度为20的string，然后根据count把string切成等长的sub-string。
    # 使用levels作为除数，用substring/levels得到的余数作为每层的文件命名
    # levels: 除数
    # count: 文件的层数

    digit = str(hashid).zfill(20)  # 将hashidber变成长度为20的string
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


if __name__ == '__main__':
    from sys import argv
    opt = argv[1]
    if opt == 'get':
        video_path = argv[2]
        audio_path = argv[3]
        get_audio(video_path, audio_path)
    elif opt == 'sub':
        ss = gen_subdirs(12826004460303937411, 256, 2)
        print('/'.join(ss))
    elif opt == 'nor':
        a = 'a:，。,+\\、b    c时代峰峻@？。～｟｠｢｣､、〃《》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟'
        n = text_normalize(a)
        print(a)
        print(n)
    else:
        print('don nothing')
