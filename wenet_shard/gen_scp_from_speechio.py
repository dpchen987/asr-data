#!/usr/bin/env python
# coding:utf-8
'''
用于从https://github.com/SpeechColab/Leaderboard
提取生成测试集
'''


import random
import os


def main(each_count=0):
    subs = os.listdir('./datasets/')
    result = []
    for s in subs:
        if s.startswith('SPEECHIO'):  # or s.startswith('AISHELL'):
            meta = os.path.join('./datasets/', s, 'metadata.tsv')
            lines = open(meta).readlines()
            dirname = os.path.dirname(os.path.abspath(meta))
            if each_count:
                zz = random.sample(lines, each_count)
            else:
                # all
                zz = lines
            zz = [(dirname, z) for z in zz]
            result.extend(zz)
    scp = open(f'z-wav_scp-{each_count}.txt', 'w')
    trans = open(f'z-trans-{each_count}.txt', 'w')
    has = set()
    for dirname, l in result:
        zz = l.strip().split()
        key = zz[0]
        if key in has:
            continue
        has.add(key)
        audio_path = os.path.join(dirname, zz[1])
        text = zz[-1]
        scp.write(f'{key}\t{audio_path}\n')
        scp.flush()
        trans.write(f'{key}\t{text}\n')
        trans.flush()
    scp.close()
    trans.close()


if __name__ == '__main__':
    import sys
    each_count = int(sys.argv[1])
    main(each_count)

