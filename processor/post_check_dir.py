#!/usr/bin/env python
# coding:utf-8


import os
import re


def dir_has_no(the_dir, reg_):
    result = []
    for root, dirs, files in os.walk(the_dir):
        has_count = 0
        for f in files:
            if re.search(reg_, f):
                has_count += 1
        if len(files) and has_count == 0:
            result.append(root)
    return result


if __name__ == '__main__':
    from sys import argv
    from pprint import pprint
    opt = argv[1]
    if opt == 'wav':
        dir_ = argv[2]
        reg_ = r'.wav'
        rr = dir_has_no(dir_, reg_)
        pprint(rr)
        print(f'{len(rr) =}')
