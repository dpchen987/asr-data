#!/usr/bin/env python
# coding:utf-8


import re
import os
import time


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


def get_duration(fp):
    cmd = f'sndfile-info {fp}'
    p = os.popen(cmd)
    out = p.read()
    d = re.findall(r'Duration.*?(\d{2}):(\d{2}):(\d{2})')[0]
    h, m, s = d
    seconds = int(h) * 3600 + int(m) * 60 + int(s)
    return seconds, ':'.join(d)


def parse_unlabeled(fp, in_dir, out_dir):
    f_labeled = fp + '.checked-lable'
    lines_origin = open(fp).readlines()
    lines_labeled = open(f_labeled).readlines()
    if len(lines_labeled) == len(lines_origin):
        print('done ', fp)
        return
    wav_scp = fp.replace('-text-', '-wav_scp-')
    wavs = {}
    with open(wav_scp) as f:
        for l in f:
            wid, path = l.strip().split()
            wavs[wid] = path
    wid = lines_labeled[-1].split()[0]
    for i, line in enumerate(lines_origin):
        if wid in line:
            i += 1
            break
    left = lines_origin[i:]
    not_long = []
    too_long = []
    for line in left:
        wid, text = line.split()
        fp_wav = wavs[wid]
        seconds, ts = get_duration(fp_wav)
        if seconds > 180:
            too_long.append(f'{ts}\t{fp_wav}\t{text}')
            print('too long', ts, fp_wav)
        else:
            not_long.append(line)
    new_fp = fp.replace(in_dir, out_dir)
    with open(new_fp, 'w') as f:
        f.write(''.join(not_long))
    return too_long


def get_unlabeled(in_dir, out_dir):
    now = time.time()
    too_long = []
    for root, dirs, files in os.walk(in_dir):
        for f in files:
            if not re.match('z-slice-text-\d\d.txt$'):
                continue
            fp = os.path.join(root, f)
            if now - os.path.getmtime(fp) < 5*60:
                print('not old', fp)
                continue
            tlong = parse_unlabeled(fp, out_dir)
            too_long.extend(tlong)

    with open('z-too-long-wave.txt', 'w') as f:
        f.write(''.join(too_long))
    print('done')


if __name__ == '__main__':
    from sys import argv
    from pprint import pprint
    opt = argv[1]
    if opt == 'p':
        fp = argv[2]
        tt, ww = process(fp)
        for i in range(len(tt)):
            print(tt[i], ww[i])
    elif opt == 'again':
        in_dir = argv[2]
        out_dir = argv[3]
        get_unlabeled(in_dir, out_dir)
    else:
        main(opt)
