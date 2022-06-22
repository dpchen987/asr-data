#!/usr/bin/env python3
# encoding:utf8

import os
import argparse

import utils
from extractor import extract


ARGS = None


def is_locked(path):
    locked = path + '.lock'
    return os.path.exists(locked)


def lock_it(path):
    locked = path + '.lock'
    with open(locked, 'w') as f:
        f.write('locked')


def unlock_it(path):
    locked = path + '.lock'
    os.remove(locked)


def process(video_path, hashid, audio_root):
    print('extracting ', video_path)
    lock_it(video_path)
    subdirs = utils.gen_subdirs(hashid, ARGS.subdir_count, ARGS.subdir_depth)
    save_dir = os.path.join(audio_root, *subdirs, str(hashid))
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        extract(video_path, save_dir, ARGS.audio_format, ARGS.cut, ARGS)
    else:
        wav_scp = f'{save_dir}/{hashid}-wav_scp.txt'
        if not os.path.exists(wav_scp):
            extract(video_path, save_dir, ARGS.audio_format, ARGS.cut, ARGS)
        else:
            print('done: ', video_path)
    if ARGS.delete_video:
        print('!!!!!!!!!!!!!!!!! delete video:', video_path)
        os.remove(video_path)
    unlock_it(video_path)


def get_args():
    parser = argparse.ArgumentParser(
            description='extract subtitle and speech from vide')
    parser.add_argument(
            '--video_dir', required=True,
            help='path to dir of video to be processed')
    parser.add_argument(
            '--extract_to_dir', required=True,
            help='dir to save extracted subtitle and speech')
    parser.add_argument(
            '--video_name_hash', default=True, action='store_true',
            help='is video name if unique hash')
    parser.add_argument(
            '--cut', default=False, action="store_true",
            help='whether to cut speech to utterance')
    parser.add_argument(
            '--subdir_count', type=int, default=512,
            help='number of subdirs of extracte_to_dir')
    parser.add_argument(
            '--subdir_depth', type=int, default=2,
            help='number of depth of subdirs')
    parser.add_argument(
            '--audio_format', default='mp3',
            help='audio format for extracted speech file')
    parser.add_argument(
            '--video_format', default='mp4',
            help='video format for extracting')
    parser.add_argument(
            '--skip_start', type=int, default=0,
            help='skip seconds at start')
    parser.add_argument(
            '--skip_end', type=int, default=0,
            help='skip seconds at end')
    parser.add_argument(
            '--delete_video', action='store_true', default=False,
            help='delete video after processing, be careful!')
    args = parser.parse_args()
    return args


def main():
    global ARGS
    ARGS = get_args()
    print(ARGS)
    for root, dirs, files in os.walk(ARGS.video_dir):
        for f in files:
            suffix = f.split('.')[-1]
            if suffix != ARGS.video_format:
                print('skip not valid video file:', f)
                continue
            path = os.path.join(root, f)
            if is_locked(path):
                continue
            hashid = utils.get_hashid(path)
            process(path, hashid, ARGS.extract_to_dir)


if __name__ == '__main__':
    main()
