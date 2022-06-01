#!/usr/bin/env python
# coding:utf-8


import re
import os
from multiprocessing import Process


def check(path_text, path_wav_scp):
    cmd = f'./label_checker_main --text {path_text} --wav_scp {path_wav_scp} --result {path_text}.checked-lable --timestamp {path_text}.checked-timestamp --model_path ~/wenet-demo/models/final.zip --dict_path ~/wenet-demo/models/words.txt --is_penalty 2'
    print(cmd)
    os.system(cmd)


def split(path_text, path_wav_scp, slice_dir, count=40):
    lines_text = open(path_text).readlines()
    lines_wave = open(path_wav_scp).readlines()
    print(f'{len(lines_text)=}, {len(lines_wave)=}')
    assert len(lines_text) == len(lines_wave)
    per = len(lines_text) // 40 + 1
    slice_text_pre = 'z-slice-text'
    slice_wav_scp_pre = 'z-slice-wav_scp'
    counter = 0
    files = []
    for i in range(0, len(lines_text), per):
        counter += 1
        ft = f'{slice_dir}/{slice_text_pre}-{counter:02}.txt'
        fw = f'{slice_dir}/{slice_wav_scp_pre}-{counter:02}.txt'
        files.append((ft, fw))
        with open(ft, 'w') as f:
            f.write(''.join(lines_text[i:i+per]))
        with open(fw, 'w') as f:
            f.write(''.join(lines_wave[i:i+per]))
    return files


def main(path_text, path_wav_scp):
    from pprint import pprint
    slice_dir = 'slice_dir2'
    slice_files = []
    for root, dirs, files in os.walk(slice_dir):
        for f in files:
            if m := re.search(r'z-slice-text-(\d+).txt$', f):
                post = m.groups(0)[0]
                wav_scp = f'z-slice-wav_scp-{post}.txt'
                ft = os.path.join(root, f)
                fw = os.path.join(root, wav_scp)
                # print(fw)
                assert os.path.exists(fw)
                slice_files.append((ft, fw))
    pprint(slice_files)
    # if not slice_files:
    #     print('==== split files ======')
    #     slice_files = split(path_text, path_wav_scp, slice_dir)
    pp = []
    for ft, fw in slice_files:
        p = Process(target=check, args=(ft, fw))
        p.start()
        pp.append(p)
        # break
    for p in pp:
        p.join()


if __name__ == '__main__':
    path_text = './speech_texts_TN.txt'
    path_wav_scp = './speech_wav_scp.txt'
    main(path_text, path_wav_scp)
