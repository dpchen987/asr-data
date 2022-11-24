#!/usr/bin/env python3


import os
import math
import argparse

ARGS = None
PIPE = None


def get_args():
    parser = argparse.ArgumentParser(
        description='To Use GPU, you need to "export CUDA_VISIBLE_DEVICES=i" firstly')
    parser.add_argument(
        '-t', '--text',
        required=True,
        help='text to TTS, one line one sentence')
    parser.add_argument(
        '-m', '--model',
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
        '-g', '--gpu_count', type=int, default=0,
        help='count of GPU to use')
    parser.add_argument(
        '-x', '--make', action='store_true',
        help='make wav_scp/text from text and wavs')
    args = parser.parse_args()
    return args


def make_scp():
    sentences = {}  # {id: text}
    sid = 0
    with open(ARGS.text) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            sentences[sid] = line
            sid += 1
    print(f'{len(sentences) = }, {sid = }')
    import os
    trans = []
    scps = []
    for root, dirs, files in os.walk(ARGS.wave_dir):
        for fn in files:
            sid = int(fn.split('_')[0])
            if sid not in sentences:
                print('invalid sid', sid)
                continue
            uttid = fn.split('.')[0]
            trans.append(f'{uttid}\t{sentences[sid]}\n')
            path = os.path.join(root, fn)
            scps.append(f'{uttid}\t{path}\n')
    print(f'{len(trans) = }, {len(scps) = }')
    trans.sort()
    scps.sort()
    with open(f'{ARGS.text}_all_trans.txt', 'w') as f:
        f.write(''.join(trans))
    with open(f'{ARGS.text}_all_scp.txt', 'w') as f:
        f.write(''.join(scps))
    print('done')


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
    gpu_id = -1
    if ARGS.gpu_count > 0:
        gpu_id = int(os.environ['CUDA_VISIBLE_DEVICES'])
        assert ARGS.gpu_count > gpu_id
    sentences = []
    i = -1
    with open(ARGS.text) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            i += 1
            if ARGS.gpu_count > 0:
                if i % ARGS.gpu_count == gpu_id:
                    sentences.append((i, line))
                else:
                    pass
            else:
                sentences.append((i, line))
    ARGS.text_id_len = int(math.log10(i)) + 1
    sub_dir_count = int(
            i * ARGS.speekers / ARGS.count_per_dir) + 1
    ARGS.sub_dir_len = int(math.log10(sub_dir_count)) + 1
    print(f'{i = }, {len(sentences) = }')
    print(ARGS)
    pool = Pool(processes=ARGS.processes)
    print('start')
    b = time.time()
    wavs = []
    for rs in pool.map(worker, sentences):
        wavs.extend(rs)
    print(f'{len(wavs) = }')
    name_txt = f'{ARGS.text}_{gpu_id}.text.txt'
    name_scp = f'{ARGS.text}_{gpu_id}.scp.txt'
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
    if ARGS.make:
        make_scp()
    else:
        main()
