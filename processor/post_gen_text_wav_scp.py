#!/usr/bin/env python
# coding:utf-8


import os


def process(fp):
    texts = []
    wavscp = []
    with open(fp) as f:
        for line in f:
            zz = line.strip().split('\t')
            if len(zz) != 2:
                # print('bad line:', line)
                continue
            wav_path = zz[0].replace('.txt', '.wav').strip()
            text = zz[1].strip()
            wav_id = wav_path.split('/')[-1]
            texts.append(f'{wav_id}\t{text}')
            wavscp.append(f'{wav_id}\t{wav_path}')
    return texts, wavscp


def main(_dir):
    f_text = open('speech_texts.txt', 'w')
    f_wavscp = open('speech_wav_scp.txt', 'w')
    for root, dirs, files in os.walk(_dir):
        for fp in files:
            if not fp.endswith('.opus.txt'):
                continue
            fp = os.path.join(root, fp)
            text, wav_scp = process(fp)
            if not text:
                continue
            f_text.write('\n'.join(text))
            f_text.write('\n')
            f_text.flush()
            f_wavscp.write('\n'.join(wav_scp))
            f_wavscp.write('\n')
            f_wavscp.flush()
    f_text.close()
    f_wavscp.close()
    cmd = 'python cn_tn.py --has_key speech_texts.txt speech_texts_TN.txt'
    print(cmd)
    os.system(cmd)


if __name__ == '__main__':
    from sys import argv
    from pprint import pprint
    opt = argv[1]
    if opt == 'p':
        fp = argv[2]
        tt, ww = process(fp)
        for i in range(len(tt)):
            print(tt[i], ww[i])
    else:
        main(opt)
