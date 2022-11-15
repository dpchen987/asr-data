#!/usr/bin/env python3


import os
import math
import argparse

ARGS = None
PIPE = None


def get_args():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument(
        '-t', '--text',
        required=True,
        help='text to TTS, one line one sentence')
    parser.add_argument(
        '-m', '--model',
        required=True,
        help='dir of model')
    parser.add_argument(
        '-s', '--speekers', type=int,
        help='number of speekers for one sentence')
    parser.add_argument(
        '-w', '--wave_dir', required=True,
        help='path to save wavs')
    parser.add_argument(
        '-p', '--processes', type=int,
        help='num of process')
    parser.add_argument(
        '-c', '--count_per_dir', type=int,
        default=1000,
        help='count per dir')
    parser.add_argument(
        '-g', '--gpu', default=False, action='store_true',
        help='use gpu')
    args = parser.parse_args()
    return args


def make_path(wav_dir, text_id, text_id_len, sub_dir_len):
    sub = text_id * ARGS.speekers // ARGS.count_per_dir
    sub_dir = os.path.join(wav_dir, f'{sub:0>{sub_dir_len}}')
    if not os.path.exists(sub_dir):
        try:
            os.makedirs(sub_dir)
        except FileExistsError:
            pass
    name = f'{text_id:0>{text_id_len}}'
    path = os.path.join(sub_dir, name)
    return path


def worker(item):
    global PIPE
    if not PIPE:
        if ARGS.gpu:
            os.environ['CUDA_VISIBLE_DEVICES'] = '0'
        # 在进程里面import paddle，否则会出现错误：
        # "The API call failed because the CUDA driver and
        # runtime could not be initialized"
        from tts_pipeline import TTSPipeline
        PIPE = TTSPipeline(ARGS.model)

    text_id, text = item
    save_path = make_path(ARGS.wave_dir,
                          text_id,
                          ARGS.text_id_len,
                          ARGS.sub_dir_len)
    print(os.getpid(), save_path)
    wavs = PIPE.tts(text, save_path, ARGS.speekers)
    return wavs


def main():
    import time
    from multiprocessing import Pool
    sentences = []
    i = 0
    with open(ARGS.text) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            sentences.append((i, line))
            i += 1
    ARGS.text_id_len = int(math.log10(len(sentences))) + 1
    sub_dir_count = int(
            len(sentences) * ARGS.speekers / ARGS.count_per_dir) + 1
    ARGS.sub_dir_len = int(math.log10(sub_dir_count)) + 1
    print(ARGS)
    pool = Pool(processes=ARGS.processes)
    print('start')
    b = time.time()
    wavs = []
    for rs in pool.map(worker, sentences):
        wavs.extend(rs)
    print(f'{len(wavs) = }')
    name_txt = f'{ARGS.text}.text.txt'
    name_scp = f'{ARGS.text}.scp.txt'
    with open(name_txt, 'w') as ftxt, open(name_scp, 'w') as fscp:
        for w in wavs:
            ftxt.write(f'{w[0]}\t{w[1]}\n')
            fscp.write(f'{w[0]}\t{w[2]}\n')
    # z = input('>')
    pool.close()
    pool.join()
    print('done, time cost:', time.time() - b)


if __name__ == "__main__":
    ARGS = get_args()
    print(ARGS)
    main()
