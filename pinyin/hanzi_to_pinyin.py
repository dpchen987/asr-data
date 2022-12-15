#!/usr/bin/env python
# coding:utf-8


import json
import random
from pypinyin import lazy_pinyin


CONFUSION = None


def load_confusion(fn):
    with open(fn) as fi:
        data = json.load(fi)
    data = {k: v.split(',') for k, v in data.items()}
    return data


def to_pinyin(hanzi, rate=0.3, total=20):
    '''
        hanzi: 汉字句子
        rate: 每句替换的最大比例
        total: 最多输出的句子数
    '''
    pys = lazy_pinyin(hanzi)
    confused = []  # [(index_origin, confusions)]
    # 1. get confused
    for i, origin in enumerate(pys):
        if origin not in CONFUSION:
            continue
        confused.append((i, CONFUSION[origin]))
    if not confused:
        return ' '.join(pys)
    # 2. choose confused
    per_max = min(int(len(pys) * 0.3), len(confused))
    result = [' '.join(pys)]
    for i in range(per_max, 0, -1):
        times = int(len(confused) / i) + 1
        print(f'replace {i} in one sentece of {len(pys) = }, {per_max = }, {times = }')
        selected = set()
        for _ in range(times):
            samples = random.sample(confused, i)
            samples.sort(key=lambda a: a[0])
            group = '-'.join([str(s[0]) for s in samples])
            if group in selected:
                continue
            print('\tgroup = ', group)
            selected.add(group)
            new = pys.copy()
            for s in samples:
                index_origin = s[0]
                confuse = random.sample(s[1], 1)
                new[index_origin] = confuse[0]
            result.append(' '.join(new))
            if len(result) >= total:
                break
        if len(result) >= total:
            break
    return result


if __name__ == '__main__':
    import sys, time
    b = time.time()
    CONFUSION = load_confusion('./py_confusion.json')
    fi = sys.argv[1]
    fo = fi + '.confusion.txt'
    with open(fi) as fin, open(fo, 'w') as fout:
        for line in fin:
            ss = to_pinyin(line.strip())
            ss = [s + '\t' + line.strip() for s in ss]
            fout.write('\n'.join(ss) + '\n')
    print('time:', time.time() - b)

