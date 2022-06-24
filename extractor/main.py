#!/usr/bin/env python3
# encoding:utf8

import time
import os
import argparse

import utils
import extractor


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


def process(video_path, hashid, audio_root, args):
    print('extracting ', video_path)
    lock_it(video_path)
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
            print('done: ', video_path)
    if args.delete_video:
        print('!!!!!!!!!!!!!!!!! delete video:', video_path)
        os.remove(video_path)
    unlock_it(video_path)


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
            help='only cut audio to utterance'
            )
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


def work(args):
    for root, dirs, files in os.walk(args.video_dir):
        for f in files:
            suffix = f.split('.')[-1]
            if suffix != args.video_format:
                print('skip not valid video file:', f)
                continue
            path = os.path.join(root, f)
            if not os.path.exists(path):
                # has been delete by other process
                continue
            if is_locked(path):
                continue
            hashid = utils.get_hashid(path)
            if not hashid:
                print('invalid name:', path)
                continue
            process(path, hashid, args.extract_to_dir, args)


def work_forever(args):
    while 1:
        work(args)
        print('======== sleep to next work loop =========')
        time.sleep(10)


def main():
    args = get_args()
    print(args)
    if args.only_cut:
        assert args.audio_dir
        only_cut(args.audio_dir, args.audio_format, 'wav')
        print('cut done')
        return
    if args.work_forever:
        worker = work_forever
    else:
        worker = work
    if args.mp < 2:
        worker(args)
        return
    # multiprocessing
    from multiprocessing import Process
    processes = [Process(target=worker, args=(args,)) for _ in range(args.mp)]
    for p in processes:
        p.start()
    for p in process:
        p.join()
    print('Bye :)')


if __name__ == '__main__':
    main()
