#!/usr/bin/env python3
# encoding:utf8

import os
import argparse

import utils
from extractor import extract


ARGS = None


def process(video_path, hashid, audio_root):
    subdirs = utils.gen_subdirs(hashid, ARGS.subdir_count, ARGS.subdir_depth)
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
