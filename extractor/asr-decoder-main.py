#!/usr/bin/env python3
# coding:utf-8


import time
import os

IDR = 'Final result:'


def parse_log(logfile, save_to):
    with open(logfile) as f:
        lines = f.readlines()
    trans = []
    rtf = 0
    for line in lines:
        if 'RTF' in line:
            print(line)
            rtf = line.split('RTF:')[-1].strip()
            continue
        if IDR not in line:
            continue
        a, b = line.split(IDR)
        uttid = a.strip().split()[-1]
        text = b.strip()
        trans.append(f'{uttid}\t{text}\n')
    with open(save_to, 'w') as f:
        f.write(''.join(trans))
    with open(f'{logfile}.rtf', 'w') as f:
        f.write(rtf)


def decode(wav_scp, args):
    begin = time.time()
    bin_dir = args.bin_dir
    model_dir = args.model_dir
    # 1. gen result name prefix according args
    result_prefix = wav_scp.rsplit('-', maxsplit=1)[0]

    os.environ['GLOG_logtostderr'] = '1'
    os.environ['GLOG_v'] = '2'
    # 2. check and set LD_LIBRARY_PATH
    names = os.listdir(bin_dir)
    for name in names:
        if name.endswith('.so') or '.so.' in name:
            os.environ['LD_LIBRARY_PATH'] = bin_dir
            break
    # 3. command for decoder_main
    onnx = False
    for name in names:
        if 'libonnxruntime.so' in name:
            onnx = True
            break
    cmds = [
        f'{bin_dir}/decoder_main --chunk_size -1 ',
        f'--wav_scp {wav_scp}',
        f'--dict_path {model_dir}/words.txt',
    ]
    if args.num_threads > 1:
        cmds.append(f'--num_threads {args.num_threads}')
    if onnx:
        print('test onnx model ...')
        cmds.append(f'--onnx_dir {model_dir}')
    else:
        cmds.append(f'--model_path {model_dir}/final.zip')
    cmds.append(f' > {result_prefix}-log.txt')
    cmds.append('2>&1')
    # cmds.append(f'| tee {result_prefix}-log.txt')
    # 4. run decoder_main
    cmd = ' '.join(cmds)
    print(cmd)
    os.system(cmd)
    # 5. parse log
    asr_trans = f'{result_prefix}-asr-trans.txt'
    parse_log(f'{result_prefix}-log.txt', asr_trans)
    timing = time.time() - begin
    print(f'done {wav_scp}, {timing=}')
    return os.getpid()


def main(args):
    import multiprocessing
    mp = 4
    pool = multiprocessing.Pool(processes=mp)
    args.num_threads //= mp
    result = []
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
            asr_trans = wav_scp.split('-wav_scp')[0] + '-asr-trans.txt'
            if os.path.exists(asr_trans):
                print('has decode', wav_scp)
                continue
            res = pool.apply_async(decode, (wav_scp, args))
            result.append(res)
            if len(result) == mp:
                res0 = result.pop(0)
                print('doen', res0.get())
    for res in result:
        print('done', res.get())
    print('done decode', args.audio_dir)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='decode wav_scp by decoder_main')
    parser.add_argument('-a', '--audio_dir', required=True, help='dir of audio to decode')
    parser.add_argument('-b', '--bin_dir', required=True, help='dir of decoder_main')
    parser.add_argument('-m', '--model_dir', required=True, help='dir of model')
    parser.add_argument('-n', '--num_threads', type=int, default=1, help='num of threads for ASR model')
    args = parser.parse_args()
    main(args)
