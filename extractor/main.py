#!/usr/bin/env python3
# encoding:utf8

import os
import argparse

import utils
from extractor import extract


ARGS = None


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


def process(video_path, hashid, audio_root):
    subdirs = gen_subdirs(hashid, ARGS.subdir_count, ARGS.subdir_depth)
    save_dir = os.path.join(audio_root, *subdirs, str(hashid))
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        extract(video_path, save_dir, ARGS.audio_format, cut=ARGS.cut)
    else:
        wav_scp = f'{save_dir}/{hashid}-wav_scp.txt'
        if not os.path.exists(wav_scp):
            extract(video_path, save_dir, ARGS.audio_format, cut=ARGS.cut)
        else:
            print('done: ', video_path)


def get_args():
    parser = argparse.ArgumentParser(description='extract subtitle and speech from vide')
    parser.add_argument('--video_dir', required=True, help='path to dir of video to be processed')
    parser.add_argument('--extract_to_dir', required=True, help='dir to save extracted subtitle and speech')
    parser.add_argument('--run_id', type=int, default=0, help='id for this run, start from 0')
    parser.add_argument('--run_total', type=int, default=1, help='total runs for multi-process')
    parser.add_argument('--video_name_hash', default=True, help='is video name if unique hash')
    parser.add_argument('--cut', default=False, action="store_true", help='whether to cut speech to utterance')
    parser.add_argument('--subdir_count', type=int, default=512, help='number of subdirs of extracte_to_dir')
    parser.add_argument('--subdir_depth', type=int, default=2, help='number of depth of subdirs')
    parser.add_argument('--audio_format', default='mp3', help='audio format for extracted speech file')
    parser.add_argument('--video_format', default='mp4', help='video format for extracting')
    args = parser.parse_args()
    return args


def main():
    global ARGS
    ARGS = get_args()
    print(ARGS)
    assert ARGS.run_id < ARGS.run_total
    for root, dirs, files in os.walk(ARGS.video_dir):
        for f in files:
            suffix = f.split('.')[-1]
            if suffix != ARGS.video_format:
                print('skip not valid video file:', f)
                continue
            path = os.path.join(root, f)
            hashid = utils.get_hashid(path)
            if hashid % ARGS.run_total != ARGS.run_id:
                continue
            process(path, hashid, ARGS.extract_to_dir)


if __name__ == '__main__':
    main()