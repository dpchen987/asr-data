#!/usr/bin/env python
# coding:utf-8


import jieba
import Levenshtein
from collections import defaultdict


add_words = ['干什么', '女的']

for w in add_words:
    jieba.add_word(w)


def choose(text_extract, text_asr):
    if text_extract == text_asr:
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
            if len(zz) != 2:
                #print('invalid', l)
                #continue
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


def gen_scp_trans(f_verify_good, f_wav_scp):
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
    pos = int(len(trans)*0.95)  # train percent: 0.95
    trans_train = trans[:pos]
    trans_test = trans[pos:]
    wav_scp_train = []
    wav_scp_test = []
    for uttid, text in trans_train:
        wav_scp_train.append(f'{uttid}\t{wav_scp[uttid]}\n')
    for uttid, text in trans_test:
        wav_scp_test.append(f'{uttid}\t{wav_scp[uttid]}\n')

    trans_train = [f'{uttid}\t{text}\n' for uttid, text in trans_train]
    trans_test = [f'{uttid}\t{text}\n' for uttid, text in trans_test]

    names = [
        ('z-good-trans-test.txt', trans_test),
        ('z-good-trans-train.txt', trans_train),
        ('z-good-wav_scp-test.txt', wav_scp_test),
        ('z-good-wav_scp-train.txt', wav_scp_train),
    ]
    for name, data in names:
        print('write', name)
        with open(name, 'w') as f:
            f.write(''.join(data))
    print('done')


if __name__ == '__main__':
    # from sys import argv
    # verify(argv[1], argv[2])
    f_verify_good = './z-verify-good.txt'
    f_wav_scp = '/aidata/audio/private/wav_scp.txt'
    gen_scp_trans(f_verify_good, f_wav_scp)
