#!/usr/bin/env python
# coding:utf-8


import re


def main():
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


main()
