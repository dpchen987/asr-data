#!/usr/bin/env python
# coding:utf-8


import re
import os
import Levenshtein
from pypinyin import pinyin, Style
import jieba

jieba.add_word('那头')

def read_file(fp, spliter):
    data = {}
    with open(fp) as f:
        for l in f:
            zz = l.strip().split(spliter, maxsplit=1)
            if len(zz) != 2:
                print(f'bad line [{l.strip()}]')
                continue
            data[zz[0]] = zz[1]
    return data


def compare(unchecked, checked):
    unchecked = unchecked.replace(' ', '')
    checked = checked.replace(' ', '')
    checked_text = re.sub(r'<[^>]*>', '', checked)
    ratio = Levenshtein.ratio(checked_text, unchecked) * 100
    if ratio >= 98:
        return ratio, checked_text
    checked_chars = []
    i = 0
    while i < len(checked):
        if checked[i] != '<':
            checked_chars.append({
                'c': checked[i],
                't': 'normal',
            })
            i += 1
            continue
        if checked[i:i+5] == '<del>':
            checked_chars.append({
                'c': '_',
                't': 'del',
            })
            i += 5
            continue
        if checked[i:i+4] == '<is>':
            pos = checked[i:].find('</is>')
            part = checked[i:i+pos+5]
            chars = re.findall('<is>(.*?)</is>', part)[0]
            for c in chars:
                checked_chars.append({
                    'c': c,
                    't': 'is',
                })
            i += pos + 5
    # print(checked, checked_chars)
    # compare two chars
    # py_unchecked = pinyin(unchecked, style=Style.NORMAL)
    good = []
    for j, c in enumerate(checked_chars):
        if c['t'] == 'normal':
            good.append(c['c'])
            continue
        if c['t'] == 'is':
            # insert的前后与其相同则丢掉insert
            if j > 0 and checked_chars[j-1]['c'] == c['c']:
                continue
            if j < len(checked_chars) - 1 and checked_chars[j+1]['c'] == c['c']:
                continue
            # 如果insert的左右成词，则丢掉
            if j > 0 and j < len(checked_chars) - 1:
                part = checked_chars[j-1]['c'] + checked_chars[j+1]['c']
                words = jieba.lcut(part, HMM=False)
                if part in words:
                    continue
                if j > 1:
                    part_3 = checked_chars[j-2]['c'] + part
                    words = jieba.lcut(part_3, HMM=False)
                    if part_3 in words:
                        continue
                if j < len(checked_chars) - 2:
                    part_3 = part + checked_chars[j+2]['c']
                    words = jieba.lcut(part_3, HMM=False)
                    if part_3 in words:
                        continue
            good.append(c['c'])
            continue
        if c['t'] == 'del':
            if j == 0:
                continue  # 首字很可能是没有这个音
            # 看看unchecked对应的是哪个字被删除了
            # 1. 往前找一段与unchecked重合的文字
            x = 1
            part_before = []
            while j-x > 0 and x < 5:
                if checked_chars[j-x]['t'] != 'normal':
                    break
                part_before.append(checked_chars[j-x]['c'])
                x += 1
            part_after = []
            x = 1
            while j+x < len(checked_chars) and x < 5:
                if checked_chars[j+x]['t'] != 'normal':
                    break
                part_after.append(checked_chars[j+x]['c'])
                x += 1
            if len(part_before) > len(part_after):
                text = ''.join(part_before)
                pos = unchecked.find(text)
                deleted = unchecked[pos+len(text)]
                good.append(deleted)
            else:
                text = ''.join(part_after)
                if not text:
                    continue
                pos = unchecked.find(text)
                deleted = unchecked[pos-1]
                good.append(deleted)
    good = ''.join(good)
    print(checked, '==>', good, '==>', unchecked)
    ratio = Levenshtein.ratio(unchecked, good) * 100
    return ratio, good


def compare2(unchecked, checked):
    '''只检查<is>数量<=2的，可能有助于修正OCR的错误
    '''
    count_th = 2
    parts = re.split(r'(<is>.*?</is>|<del>)' , checked)
    if len(parts) == 1:
        return 100, unchecked
    unchecked = unchecked.replace(' ', '')
    pp = [p for p in parts]  # if p[0] != '<']
    parts_unchecked = re.split(f"({'|'.join(pp)})" , unchecked)
    print(f'{parts=}')
    print(f'{parts_unchecked=}')
    # if len(parts) > count_th:
    #     checked_text = re.sub(r'<[^>]*>', '', checked).replace(' ', '')
    #     ratio = Levenshtein.ratio(checked_text, unchecked) * 100
    #     return ratio, unchecked 
    good = []
    unchecked_i = 0
    for i, p in enumerate(parts):
        if p[0] != '<':
            good.append(p)
            continue
        if p[:4] == '<is>':
            chars = re.findall('<is>(.*?)</is>', p)[0]
            unchecked_char = ''
            if i > 0:
                pos = unchecked.find(parts[i-1])
                if pos > -1:
                    unchecked_i = pos+len(parts[i-1])
                    unchecked_char = unchecked[unchecked_i]
            if not unchecked_char and i < len(parts) - 1:
                pos = unchecked.find(parts[i+1])
                if pos > -1:
                    unchecked_i = pos - 1
                    unchecked_char = unchecked[unchecked_i]
            if chars == unchecked_char:
                good.append(chars)
            else:
                py_chars = pinyin(chars, style=Style.NORMAL)
                py_chars = '-'.join([p[0] for p in py_chars])
                py_unchecked_char = pinyin(unchecked_char, style=Style.NORMAL)
                py_unchecked_char = '-'.join([p[0] for p in py_unchecked_char])
                if py_chars == py_unchecked_char:
                    good.append(unchecked_char)
        if p[:5] == '<del>':
            if i > 0:
                pos = unchecked.find(parts[i-1])
                if pos > -1:
                    good.append(unchecked[pos+len(parts[i-1])])
            if i < len(parts) - 1:
                pos = unchecked.find(parts[i+1])
                if pos > -1:
                    good.append(unchecked[pos-1])

    good = ''.join(good)
    print(checked, '==>', good, '==>', unchecked)
    ratio = Levenshtein.ratio(unchecked, good) * 100
    return ratio, good


def process(fp_checked):
    '''比较校对和未校对的相似度'''
    unchecked = fp_checked.replace('.checked-lable', '')
    wav_scp = unchecked.replace('-text-', '-wav_scp-')
    unchecked = read_file(unchecked, '\t')
    wav_scp = read_file(wav_scp, '\t')
    checked = read_file(fp_checked, ' ')
    scopes = [
        [98, 101],  # left-open, right-closed
        [97, 98],
        [96, 97],
        [95, 96],
        [90, 95],
        [80, 90],
        [50, 80],
        [00, 50],
    ]
    results = {}
    for s in scopes:
        key = f'{s[0]}-{s[1]}'
        results[key] = []

    for wid, v in checked.items():
        ratio, good = compare2(unchecked[wid], v)
        if len(good) < 2:
            continue
        for s in scopes:
            if s[0] <= ratio < s[1]:
                break
        key = f'{s[0]}-{s[1]}'
        results[key].append([wid, unchecked[wid], good, v])
    return results


def main(in_dir):
    results = {}
    for root, dirs, files in os.walk(in_dir):
        for f in files:
            if not f.endswith('-lable'):
                continue
            fp = os.path.join(root, f)
            print('processing', fp)
            res = process(fp)
            for k, v in res.items():
                if k in results:
                    results[k].extend(v)
                else:
                    results[k] = v
            break
    total = 0
    for k, v in results.items():
        # print(f'{k} : {len(v)}')
        total += len(v)
        fn = f'z-speech-text_{k}.txt'
        lines = ['\t'.join(m) for m in v]
        with open(fn, 'w') as f:
            f.write('\n'.join(lines))
    for k, v in results.items():
        print(f'{k} : {len(v)}, {len(v)/total}')
    print('done')


if __name__ == '__main__':
    checked = '电话那<is>腾</is>头儿子<del>好<is>安</is>一<is>散</is>时松了一口<is>口</is>气'
    unchecked = '电话那头儿子安好庞阿姨暂时松了一口气'
    # unchecked = '所以基本上我觉得这样啊如果他要做这个职业'
    # checked = '所以基本上我觉得这样<is>好</is>如果他要做这个职业'
    unchecked = '当时这名举报者小王向惠州警方透露一个星期前他在朋友介绍下去了当地一个刚开起来的地下赌场玩'
    checked = '当时<is>请</is>举报者小王向惠州警方透露一个星期前他在朋友<is>就</is>介绍下去了当地一个<del>开起来的地下赌场玩'
    unchecked = '没提过心里舒服吗'
    checked = '没<is>停</is>心里舒服吗'
    unchecked = '角管你怎么激我我也不会'
    checked = '<is>甭</is>管你怎么激我我也不会'
    r, good = compare2(unchecked, checked)
    print(r)
    print(good)
    from sys import argv
    in_dir = argv[1]
    main(in_dir)
