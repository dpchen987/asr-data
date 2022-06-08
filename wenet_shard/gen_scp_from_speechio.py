#!/usr/bin/env python
# coding:utf-8
'''
用于从https://github.com/SpeechColab/Leaderboard
提取生成测试集
'''


import random
import os


def main(data_dir, each_count, save_name):
    # _dir : path-to-Leaderboard/datasets
    subs = os.listdir(data_dir)
    result = []
    for s in subs:
        if s.startswith('SPEECHIO') or s.startswith('AISHELL'):
            meta = os.path.join(data_dir, s, 'metadata.tsv')
            lines = open(meta).readlines()
            dirname = os.path.dirname(os.path.abspath(meta))
            if each_count:
                zz = random.sample(lines, each_count)
            else:
                # all
                zz = lines
            zz = [(dirname, z) for z in zz]
            result.extend(zz)
    scp = open(f'{save_name}-{each_count}-wav_scp.txt', 'w')
    trans = open(f'{save_name}-{each_count}-trans.txt', 'w')
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
    import argparse
    parser = argparse.ArgumentParser(description='select data for test-set')
    parser.add_argument('--count', type=int, required=True, help="select count from each set")
    parser.add_argument('--dir', required=True, help="dir to Leaderboard/datasets")
    parser.add_argument('--save', required=True, help="file path of wav_scp to save")
    args = parser.parse_args()
    main(args.dir, args.count, args.save)

