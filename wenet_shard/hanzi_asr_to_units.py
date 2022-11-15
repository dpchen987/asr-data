#!/usr/bin/env python
# coding:utf-8


import re

P_HANZI = re.compile(r'[\u4E00-\u9FA5]+')


def gen_units():
    name = './hanzi_asr.txt'
    hanzi = []
    with open(name) as f:
        for line in f:
            zi = line.strip()
            if not zi:
                continue
            hanzi.append(zi)
    hanzi.sort()
    head = ['<blank>', '<unk>', '▁'] + [chr(i) for i in range(65, 65+26)]
    units = head + hanzi + ['<sos/eos>']
    lines = [f'{c} {i}\n' for i, c in enumerate(units)]
    with open('units.txt', 'w') as f:
        f.write(''.join(lines))
    print('done, tokens:', len(units))


def check_oov(fn):
    units = set()
    with open('./hanzi_asr.txt') as f:
        for line in f:
            zi = line.strip()
            if not zi:
                continue
            units.add(zi)
    oov_count = 0
    with open(fn) as f:
        for line in f:
            hanzi = ''.join(P_HANZI.findall(line))
            for zi in hanzi:
                if zi not in units:
                    print('oov:', zi, line)
                    oov_count += 1
    print(f'{oov_count = }')


if __name__ == "__main__":
    from sys import argv
    if len(argv) > 1:
        fn = argv[1]
        check_oov(fn)
    else:
        gen_units()
