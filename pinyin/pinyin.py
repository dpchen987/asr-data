from pypinyin import lazy_pinyin
from itertools import combinations
import random
from collections import Counter
import json
import sys


# 从给定的x向下range，until range到1或count>comb_count
def comb(start, idx_li, comb_count):
    count = 0
    comb_li = []
    for i in range(start, 0, -1):
        comb = combinations(idx_li, i)
        for j in list(comb):
            comb_li.append(j)
            count += 1
            if count >= comb_count:
                return comb_li
    return comb_li


# 生成每一个文本对应的多条拼音
def change_py(py_li, selected_numbers, py_dic):
    change_li = [' '.join(py_li).replace(' \t', '\t')]
    for i in selected_numbers:
        count = Counter(i)
        change_dic = {}
        for j in count:
            value = py_dic[py_li[j]][str(count[j])]    # 在谐音dict中找到该拼音对应的谐音
            change_dic[j] = random.sample(value, k=1)[0]

        # change pinyin
        change = py_li.copy()
        for k in change_dic:
            change[k] = change_dic[k]
        change_li.append(' '.join(change).replace(' \t', '\t'))
    return change_li


def to_pinyin(txt, choose=0.3, x=0.5, n=20):
    """
    x: 一句话最多可以被替代多少个词的比例
    choose: 从所有替代拼音中随机选出的比例
    n: 一句话最多可以变成的拼音数量
    """
    # 读入谐音dict
    with open('py.json', 'r') as fp:
        py_dic = json.load(fp)

    idx_li = []
    py_li = lazy_pinyin(txt)    # 生成拼音list
    py_li += [f'\t{txt}']
#     print(py_li)
    # 找到可以替代的拼音并将idx存在idx_li
    for idx, py in enumerate(py_li):
        if py in py_dic.keys():
            if isinstance(py_dic[py], str):
                idx_li.append(idx)
            else:
                idx_li += [idx]*len(py_dic[py])

    comb_count = round(n/choose)    # 需要的combination数量由n和choose决定
    start = min(len(set(idx_li)), round(len(py_li)*x))

    comb_li = comb(start, idx_li, comb_count)
    selected_numbers = random.sample(comb_li, k=min(len(comb_li), n))    # 随机选取n条生成的拼音

    return change_py(py_li, selected_numbers, py_dic)


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as f:
        lines = f.readlines()

    result = []
    for i, line in enumerate(lines):
        line = line.replace('\n', '')
        result += to_pinyin(line)
        if i%100==0:
            print(f"{i}/{len(lines)} are done")

    with open('pinyin.txt', 'w') as f:
        for line in result:
            f.write(f"{line}\n")