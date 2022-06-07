#!/usr/bin/env python
# coding:utf-8
'''
从视频中提取字幕、语音并对齐后，我们得到了初步的语音标注数据。
然后，用ASR转写语音得到转写文本
本工具对比提取的文本和ASR转写文本，选出最优文本，得到最终的标注数据。
'''


import jieba
import Levenshtein
from collections import defaultdict


add_words = ['干什么', '女的']

for w in add_words:
    jieba.add_word(w)


def choose(text_extract, text_asr):
    # need more reasonable rules To Be Added
    if text_extract == text_asr:
        return text_extract, 100
    if text_extract in text_asr:
        # 此种情况：语音头或尾有文字，而字幕没有，以ASR为准
        return text_asr, 99
    if text_asr in text_extract:
        # 语音不包含字幕的头或尾，以ASR为准
        return text_extract, 100
    distance = Levenshtein.distance(text_extract, text_asr)
    if distance < 3:
        words_extract = jieba.lcut(text_extract)
        words_asr = jieba.lcut(text_asr)
        if len(words_asr) >= len(words_extract):
            return text_extract, 99
        return text_asr, 99
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


def verify(f_extract, f_asr):
    texts_extract = read(f_extract)
    print(f'{len(texts_extract)=}')
    texts_asr = read(f_asr)
    print(f'{len(texts_asr)=}')
    result = defaultdict(list)
    for uttid, text in texts_extract.items():
        if uttid not in texts_asr:
            print('no asr', uttid)
            result['00'].append((uttid, text))
            continue
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
        name = f'z-verify-{k}.txt'
        lines = ["\t".join(i) for i in v]
        with open(name, 'w') as f:
            f.write('\n'.join(lines))
            f.write('\n')
    print('done')


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


def main():
    import argparse
    parser = argparse.ArgumentParser(description="verify and split")
    parser.add_argument('cmd', choices=['verify', 'split'], help="verify or split")
    parser.add_argument('--text_extract', help='text extraced for verify')
    parser.add_argument('--text_asr', help='text by asr for verify')
    parser.add_argument('--text', help='text for split')
    parser.add_argument('--scp', help='wav_scp for split')
    args = parser.parse_args()
    if args.cmd == 'verify':
        verify(args.text_extract, args.text_asr)
    else:
        split_data(args.text, args.scp)



if __name__ == '__main__':
    main()
