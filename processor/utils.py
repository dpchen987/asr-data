#!/usr/bin/env python3

import os
import re
import difflib


differ = difflib.SequenceMatcher(isjunk=lambda x: x==' ')


def save_list(list_data, file_path):
    with open(file_path, 'w') as f:
        for t in list_data:
            z = [str(i) for i in t]
            s = "\t".join(z)
            line = f'{s}\n'
            f.write(line)
    

def read_list(fiel_path):
    items = []
    with open(fiel_path) as f:
        for line in f:
            zz = line.strip().split('\t')
            item = [int(i) if i.isdigit() else i for i in zz]
            items.append(item)
    return items


def text_normalize(text):
    non_stop_puncs = (r'[＂＃＄％＆＇（）＊＋，。－／：；＜＝＞＠［＼］＾＿｀｛｜｝'
                      r'～｟｠｢｣､、〃《》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾'
                      r'!"#$%&\'()*+,-./:;<=>?@\[\\\]^_`{|}~'
                      r'〿–—‘’‛“”„‟…‧﹏]+')
    text = re.sub(non_stop_puncs, '', text)
    return text


def calc_similary(t1, t2):
    differ.set_seq1(t1)
    differ.set_seq2(t2)
    return differ.ratio()


def get_audio(video_path, audio_path, channel=1, samplerate=48000, bitrate=32000):
    args = [
        f'-ac {channel}',
        f'-ar {samplerate}',
        f'-ab {bitrate}',
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



if __name__ == '__main__':
    from sys import argv
    opt = argv[1]
    if opt == 'get':
        video_path = argv[2]
        audio_path = argv[3]
        get_audio(video_path, audio_path)
    elif opt == 'nor':
        a = 'a:，。,+\\、'
        n = text_normalize(a)
        print(a)
        print(n)
    else:
        print('don nothing')