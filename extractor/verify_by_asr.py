#!/usr/bin/env python
# coding:utf-8
'''
从视频中提取字幕、语音并对齐后，我们得到了初步的语音标注数据。
然后，用ASR转写语音得到转写文本
本工具对比提取的文本和ASR转写文本，选出最优文本，得到最终的标注数据。
'''


import os
import Levenshtein
from pypinyin import pinyin, Style
from collections import defaultdict
from textnorm_zh import text_norm


def choose(text_extract, text_asr):
    text_extract = text_norm(text_extract)
    # need more reasonable rules To Be Added
    if text_extract == text_asr:
        return text_extract, 100
    if text_extract in text_asr:
        # 此种情况：语音头或尾有文字，而字幕没有，以ASR为准
        return text_asr, 99
    if text_asr in text_extract:
        # 语音不包含字幕的头或尾，以ASR为准
        return text_asr, 99
    # 看拼音
    py_extract = pinyin(text_extract, Style.FIRST_LETTER)
    py_extract = ''.join([a[0] for a in py_extract])
    py_asr = pinyin(text_asr, Style.FIRST_LETTER)
    py_asr = ''.join([a[0] for a in py_asr])
    if py_extract == py_asr:
        # 音相同，去字幕
        print(f'same pinyin {text_extract=}, {text_asr=}')
        return text_extract, 100
    if py_extract in py_asr or py_asr in py_extract:
        return text_asr, 99
    distance = Levenshtein.distance(py_extract, py_asr)
    ratio = Levenshtein.ratio(py_extract, py_asr)
    if distance < 4 and ratio > 0.8:
        # 有个问题：OCR识别错字，但ASR识别正确，如何取舍？
        # 比如：’耍赖', OCR识别为'要赖'
        return text_extract, 98
    ratio = Levenshtein.ratio(text_extract, text_asr)
    return text_extract, ratio


def read(fp):
    tt = {}
    with open(fp) as f:
        for l in f:
            zz = l.strip().split('\t')
            if len(zz) > 2:
                print('invalid', l)
                continue
            if len(zz) == 1:
                zz.append('')
            if zz[0] not in tt:
                tt[zz[0]] = zz[1]
            else:
                if len(zz[1]) > len(tt[zz[0]]):
                    tt[zz[0]] = zz[1]
    return tt


def verify(f_extract, f_asr, f_save):
    texts_asr = read(f_asr)
    if len(texts_asr) < 50:
        print(f'too few speech in {f_asr}, skip it!')
        return 0
    texts_extract = read(f_extract)
    result = defaultdict(list)
    duration_max = 60  # seconds
    duration_total = 0
    for uttid, text in texts_extract.items():
        if uttid not in texts_asr:
            print('no asr', uttid)
            result['00'].append((uttid, text))
            continue
        begin, end = uttid.split('_')[1].split('-')
        duration = (int(end) - int(begin)) / 1000
        if duration > duration_max:
            # 模型最大支持的position encoding为5000，即200*(1000ms/40ms)
            # print(f'too long speech: {duration=} > {duration_max=} seconds, {uttid}')
            continue
        duration_total += duration
        good, ratio = choose(text, texts_asr[uttid])
        if ratio == 100:
            result['100'].append((uttid, good))
        elif ratio >= 99:
            result['99'].append((uttid, good, text, texts_asr[uttid]))
        elif ratio >= 96:
            result['96'].append((uttid, good, text, texts_asr[uttid]))
        elif ratio >= 80:
            result['80'].append((uttid, good, texts_asr[uttid]))
        else:
            result['xx'].append((uttid, good, text, texts_asr[uttid]))
    for k, v in result.items():
        name = f'{f_save}-{k}.txt'
        lines = ["\t".join(i) for i in v]
        with open(name, 'w') as f:
            f.write('\n'.join(lines))
            f.write('\n')
    return duration_total


def split_data(f_verify_good, f_wav_scp):
    wav_scp = read(f_wav_scp)
    trans = []
    count = 0
    with open(f_verify_good) as f:
        for l in f:
            count += 1
            zz = l.strip().split('\t')
            uttid = zz[0]
            if uttid not in wav_scp:
                continue
            text = zz[1]
            trans.append((uttid, text))
    print(f'{len(trans)=}, {count=}')
    print('shuffle to test, train')
    import random
    random.shuffle(trans)
    # train:test:dev = 9:0.5:0.5
    pos1 = int(len(trans)*0.90)
    pos2 = int(len(trans)*0.95)
    train_trans = trans[:pos1]
    test_trans = trans[pos1:pos2]
    dev_trans = trans[pos2:]
    train_scp = [f'{uttid}\t{wav_scp[uttid]}\n' for uttid, text in train_trans]
    test_scp = [f'{uttid}\t{wav_scp[uttid]}\n' for uttid, text in test_trans]
    dev_scp = [f'{uttid}\t{wav_scp[uttid]}\n' for uttid, text in dev_trans]

    train_trans = [f'{uttid}\t{text}\n' for uttid, text in train_trans]
    test_trans = [f'{uttid}\t{text}\n' for uttid, text in test_trans]
    dev_trans = [f'{uttid}\t{text}\n' for uttid, text in dev_trans]

    names = [
        ('z-good-trans-dev.txt', dev_trans),
        ('z-good-trans-test.txt', test_trans),
        ('z-good-trans-train.txt', train_trans),
        ('z-good-wav_scp-dev.txt', dev_scp),
        ('z-good-wav_scp-test.txt', test_scp),
        ('z-good-wav_scp-train.txt', train_scp),
    ]
    for name, data in names:
        print('write', name)
        with open(name, 'w') as f:
            f.write(''.join(data))
    print('done')


def verify_dir(audio_dir):
    duration_total = 0
    for root, dirs, files in os.walk(audio_dir):
        for f in files:
            if not f.endswith('-asr-trans.txt'):
                continue
            f_extract = os.path.join(root, f.replace('-asr-trans.txt', '-trans.txt'))
            assert os.path.exists(f_extract)
            f_asr = os.path.join(root, f)
            f_save = f_extract.rsplit('-', maxsplit=1)[0] + '-verified'
            d = verify(f_extract, f_asr, f_save)
            duration_total += d
    print(f'done, {duration_total=}')


def merge(audio_dir):
    def read_list(fp):
        items = []
        with open(fp) as f:
            for ln in f:
                zz = ln.strip().split('\t')
                items.append(zz)
        return items
    duration_total = 0
    lines_trans = []
    lines_scps = []
    for root, dirs, files in os.walk(audio_dir):
        for f in files:
            if not f.endswith('-asr-trans.txt'):
                continue
            names = [
                f.replace('-asr-trans.txt', '-verified-100.txt'),
                f.replace('-asr-trans.txt', '-verified-99.txt'),
                f.replace('-asr-trans.txt', '-verified-96.txt'),
                ]
            f_wav_scp = os.path.join(root, f.replace('-asr-trans.txt', '-wav_scp.txt'))
            wav_scps = read(f_wav_scp)
            print(f'merging {f_wav_scp}, {len(wav_scps)=}')
            for name in names:
                fp = os.path.join(root, name)
                if not os.path.exists(fp):
                    print('\tno file', fp)
                    continue
                trans = read_list(fp)
                for t in trans:
                    uttid = t[0]
                    begin, end = uttid.split('_')[1].split('-')
                    duration = (int(end) - int(begin)) / 1000
                    duration_total += duration
                    text = t[1]
                    lines_trans.append(f'{uttid}\t{text}\n')
                    fp_wav = wav_scps[uttid]
                    lines_scps.append(f'{uttid}\t{fp_wav}\n')
    with open('z-merged-trans.txt', 'w') as f:
        f.write(''.join(lines_trans))
    with open('z-merged-wav_scp.txt', 'w') as f:
        f.write(''.join(lines_scps))
    print(f'done, {duration_total=}, {len(lines_scps)=}')


def main():
    import argparse
    parser = argparse.ArgumentParser(description="verify and split")
    parser.add_argument('cmd', choices=['verify', 'split', 'merge'], help="verify or split or merge")
    parser.add_argument('--audio_dir', help='audio dir to be verified')
    parser.add_argument('--text_extract', help='text extraced for verify')
    parser.add_argument('--text_asr', help='text by asr for verify')
    parser.add_argument('--text', help='text for split')
    parser.add_argument('--scp', help='wav_scp for split')
    args = parser.parse_args()
    if args.cmd == 'verify':
        if args.audio_dir:
            verify_dir(args.audio_dir)
        else:
            verify(args.text_extract, args.text_asr)
    elif args.cmd == 'merge':
        merge(args.audio_dir)
    else:
        split_data(args.text, args.scp)


if __name__ == '__main__':
    main()
