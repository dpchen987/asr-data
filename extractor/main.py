#!/usr/bin/env python3
# encoding:utf8

import time
import os
import argparse

import utils
import extractor
from logger import logger


def process(video_path, hashid, audio_root, args):
    logger.info(f'extracting: {video_path}')
    b = time.time()
    utils.lock_it(video_path)
    subdirs = utils.gen_subdirs(hashid, args.subdir_count, args.subdir_depth)
    save_dir = os.path.join(audio_root, *subdirs, str(hashid))
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        extractor.extract(
                video_path,
                save_dir, args.audio_format, args.cut, args)
    else:
        wav_scp = f'{save_dir}/{hashid}-wav_scp.txt'
        if not os.path.exists(wav_scp):
            extractor.extract(
                    video_path, save_dir, args.audio_format, args.cut, args)
        else:
            logger.info('done: ', video_path)
    if args.delete_video:
        logger.info(f'!!!!!!!!!!!!!!!!! delete video: {video_path}')
        os.remove(video_path)
    utils.unlock_it(video_path)
    e = time.time()
    logger.info(f'done extracting {video_path}, time cost:{e-b}')


def get_args():
    parser = argparse.ArgumentParser(
            description='extract subtitle and speech from vide')
    parser.add_argument(
            '--video_dir',
            help='path to dir of video to be processed')
    parser.add_argument(
            '--audio_dir',
            help='dir to save extracted subtitle and speech')
    parser.add_argument(
            '--only_cut', default=False, action='store_true',
            help='only cut audio to utterance')
    parser.add_argument(
            '--mp', type=int, default=1,
            help="number of processes for multiprocessing")
    parser.add_argument(
            '--run_forever', default=True, action='store_true',
            help='run forever what if new video added')
    parser.add_argument(
            '--video_name_hash', default=True, action='store_true',
            help='is video name if unique hash')
    parser.add_argument(
            '--log_level', default='info',
            help='set logging level, default is info')
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


def only_cut(audio_dir, audio_format, save_format):
    for root, dirs, files in os.walk(audio_dir):
        for f in files:
            if not f.endswith(audio_format):
                continue
            segment_dir = os.path.join(root, save_format)
            fp_timeline = os.path.join(root, f.split('.')[0] + '-timeline.txt')
            if not os.path.exists(fp_timeline):
                print('no file', fp_timeline)
                continue
            timeline = utils.read_list(fp_timeline)
            if os.path.exists(segment_dir):
                print('has cut', f)
                segs = os.listdir(segment_dir)
                if len(segs) == len(timeline):
                    continue
                print('\tbut it seems only part of all', f'{len(segs)=}, {len(timeline)}')
            audio_file = os.path.join(root, f)
            print('cutting', audio_file)
            extractor.timeline_to_scp_cut(audio_file, timeline, save_format)
    print('cutting done')


def run(args):
    for root, dirs, files in os.walk(args.video_dir):
        for f in files:
            suffix = f.split('.')[-1]
            if suffix != args.video_format:
                logger.warn(f'skip not valid video file: {f}')
                continue
            path = os.path.join(root, f)
            if not os.path.exists(path):
                # has been delete by other process
                continue
            if utils.is_locked(path):
                continue
            hashid = utils.get_hashid(path)
            if not hashid:
                logger.error(f'invalid name: {path}')
                continue
            process(path, hashid, args.audio_dir, args)


def run_forever(args):
    to_sleep = 10
    while 1:
        run(args)
        logger.info('======== sleep {to_sleep} to next run loop =========')
        time.sleep(to_sleep)


def main():
    args = get_args()
    print(f'{args=}')
    if args.only_cut:
        assert args.audio_dir
        only_cut(args.audio_dir, args.audio_format, 'wav')
        return
    if args.run_forever:
        runner = run_forever
    else:
        runner = run
    if args.mp < 2:
        runner(args)
        return
    # multiprocessing
    from multiprocessing import Process
    processes = [Process(target=runner, args=(args,)) for _ in range(args.mp)]
    for p in processes:
        p.start()
    for p in process:
        p.join()
    print('Bye :)')


if __name__ == '__main__':
    main()
