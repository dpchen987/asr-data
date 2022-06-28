#!/usr/bin/env python3
# coding:utf-8


import time
import os
import asyncio

from ws_query import ws_rec
import utils


def read(wav_scp):
    with open(wav_scp) as f:
        lines = f.readlines()
    items = []
    for l in lines:
        uttid, path = l.strip().split('\t')
        items.append((uttid, path))
    return items


async def decode(wav_scp, args):
    utils.lock_it(wav_scp)
    begin = time.time()
    trans = []
    wavs = read(wav_scp)
    tasks = []
    for uttid, path in wavs:
        with open(path, 'rb') as f:
            data = f.read()
        t = asyncio.create_task(ws_rec(data))
        tasks.append((uttid, t))
        if len(tasks) < args.multi_coro:
            continue
        for _uttid, _t in tasks:
            try:
                text = await _t
            except Exception as e:
                print('exception:', e)
                text = ''
            trans.append(f'{_uttid}\t{text}\n')
        tasks = []
    for _uttid, _t in tasks:
        try:
            text = await _t
        except Exception as e:
            print('exception:', e)
            text = ''
        trans.append(f'{_uttid}\t{text}\n')
    asr_trans = wav_scp.split('-wav_scp')[0] + '-asr-trans.txt'
    if len(trans) != len(wavs):
        print('==================== not equal', len(trans), len(wavs))
    with open(asr_trans, 'w') as f:
        f.write(''.join(trans))
    timing = time.time() - begin
    print(f'done {wav_scp}, {timing=}')
    utils.unlock_it(wav_scp)


def main(args):
    for root, dirs, files in os.walk(args.audio_dir):
        for f in files:
            if not f.endswith('-wav_scp.txt'):
                continue
            wavs = os.path.join(root, 'wav')
            if not os.path.exists(wavs):
                # the mp3 has not been cut to wav
                print(f'=========== {f} not been cut')
                continue
            wav_scp = os.path.join(root, f)
            if utils.is_locked(wav_scp):
                continue
            asr_trans = wav_scp.split('-wav_scp')[0] + '-asr-trans.txt'
            if os.path.exists(asr_trans):
                print('has decode', wav_scp)
                continue
            asyncio.run(decode(wav_scp, args))
    print('done decode', args.audio_dir)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='decode wav_scp by decoder_main')
    parser.add_argument('-a', '--audio_dir', required=True, help='dir of audio to decode')
    parser.add_argument('-m', '--multi_coro', type=int, default=1, help='num of coroutines')
    args = parser.parse_args()
    main(args)
