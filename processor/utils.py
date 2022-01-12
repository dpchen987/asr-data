#!/usr/bin/env python3

import re
import difflib


differ = difflib.SequenceMatcher(isjunk=lambda x: x==' ')


def save_list(list_data, file_path):
    with open(file_path, 'w') as f:
        for t in list_data:
            z = [str(i) for i in t]
            s = "\t".join(z)
            line = f'{s}\n'
            f.write(line)
    

def read_list(fiel_path):
    items = []
    with open(fiel_path) as f:
        for line in f:
            zz = line.strip().split('\t')
            item = [int(i) if i.isdigit() else i for i in zz]
            items.append(item)
    return items


def text_normalize(text):
    non_stop_puncs = (r'[＂＃＄％＆＇（）＊＋，。－／：；＜＝＞＠［＼］＾＿｀｛｜｝'
                      r'～｟｠｢｣､、〃《》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾'
                      r'!"#$%&\'()*+,-./:;<=>?@\[\\\]^_`{|}~'
                      r'〿–—‘’‛“”„‟…‧﹏]+')
    text = re.sub(non_stop_puncs, '', text)
    return text


def calc_similary(t1, t2):
    differ.set_seq1(t1)
    differ.set_seq2(t2)
    return differ.ratio()


if __name__ == '__main__':
    from sys import argv
    opt = argv[1]
    if opt == 'nor':
        a = 'a:，。,+\\、'
        n = text_normalize(a)
        print(a)
        print(n)
    else:
        print('don nothing')