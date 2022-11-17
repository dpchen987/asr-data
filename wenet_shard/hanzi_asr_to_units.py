#!/usr/bin/env python
# coding:utf-8


import re
import time
import csv
import argparse

P_HANZI = re.compile(r'[\u4E00-\u9FA5]+')


def read():
    name = './hanzi-通用规范汉字表.csv'
    print('start read')
    b = time.time()
    hanzi = []
    with open(name) as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            level = float(row['ASR等级'])
            if level >= 3:
                continue
            zi = row['汉字']
            hanzi.append(zi)
    print('read done', time.time() - b)
    return hanzi


def gen_units():
    hanzi = read()
    hanzi.sort()
    head = ['<blank>', '<unk>', '▁'] + [chr(i) for i in range(65, 65+26)]
    units = head + hanzi + ['<sos/eos>']
    lines = [f'{c} {i}\n' for i, c in enumerate(units)]
    with open('units.txt', 'w') as f:
        f.write(''.join(lines))
    print('done, tokens:', len(units))


def check_oov(fn):
    units = read()
    oov = set()
    with open(fn) as f:
        for line in f:
            hanzi = ''.join(P_HANZI.findall(line))
            for zi in hanzi:
                if zi not in units:
                    print('oov:', zi, line)
                    oov.add(zi)
    print(oov)
    print(f'{len(oov) = }')


def get_args():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument(
        '-o', '--option',
        choices=['gen', 'oov'],
        help='options to do')
    parser.add_argument(
        '-f', '--file',
        help='file to check oov')
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = get_args()
    if args.option == 'gen':
        gen_units()
    elif args.option == 'oov':
        check_oov(args.file)
    else:
        print('invalid option:', args.option)
