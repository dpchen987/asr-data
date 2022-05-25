#!/usr/bin/env python
# coding:utf-8
import os
import re
import soundfile as sf
import librosa
from collections import Counter
from utils import calc_similary, read_list, save_list
SIM_THRESH = 0.8


def align_them(speeches, subtitles):
    ''' raw subtitles: [(timestamp, text), ...]
    '''
    # 掐头去尾3分钟，语音范围内的字幕都一样，则语音和字幕为good，否则bad
    skip_start = 1*60*1000  # milliseconds
    skip_end = speeches[-1][0] - 3*60*1000  # milliseconds
    goods = []
    bads = []
    i = 0  # index of speeches
    j = 0  # index of subtitles
    #print(f'{ len(speeches) = }')
    for i, spch in enumerate(speeches):
        speech_start, speech_end = spch
        if speech_start < skip_start:
            continue
        if speech_start > skip_end:
            continue
        # 先跳到跟本段语音重合的字幕
        while j < len(subtitles):
            if speech_start <= int(subtitles[j][0]):
                break
            j += 1
        if j == len(subtitles) - 1:
            break
        subs = []
        while j < len(subtitles):
            if speech_end < subtitles[j][0]:
                break
            # print(type(subtitles[j][1]), f'{subtitles[j][1]=}')
            text = re.sub(r'\s+', '', str(subtitles[j][1]))
            if text:
                subs.append(text)
            j += 1
        if not subs:
            # print('== no subtitle :', speech_start, speech_end, 'j=', j)
            bads.append([speech_start, speech_end, 'no-subtitle'])
            continue

        # 检查语音范围内的字幕是否相同，相同则为good
        groups = [[subs[0]]]
        for m in range(1, len(subs)):
            sim = calc_similary(subs[m-1], subs[m])
            if sim < SIM_THRESH:
                groups.append([subs[m]])
            else:
                groups[-1].append(subs[m])
        if len(groups) == 1:
            sub_goods = groups[0]
            c = Counter(sub_goods)
            sub_good = c.most_common()[0][0]
        else:
            sub_goods = []
            skiped = []
            for i, g in enumerate(groups):
                if (i == 0 or i == len(groups)-1) and len(g) == 1:
                    skiped += g
                    continue
                c = Counter(g)
                sub_goods.append(c.most_common()[0][0])
            if sub_goods:
                sub_good = ''.join(sub_goods)
            else:
                sub_good = ''.join(skiped)
        if goods and goods[-1][-1] == sub_good:
            # 与上一个语音字幕相同则合并这两条语音
            goods[-1][1] = speech_end
        else:
            goods.append([speech_start, speech_end, sub_good])
    return goods, bads


def align_merge(timeline):
    goods = [timeline[0]]
    for i in range(1, len(timeline)):
        # rule-1:
        # 1 len <=3
        # 2 len < 6
        # do not compare
        t_last = goods[-1][2]
        t_this = timeline[i][2]
        if len(t_last) <= 3 and len(t_this) < 2*len(t_last):
            goods.append(timeline[i])
            continue
        # rule-2:
        # 1 abc
        # 2 abcdef
        # 上一行包含在本行，合并两行，取本行的文本
        if len(t_last) <= len(t_this):
            sim = calc_similary(t_last, t_this[:len(t_last)])
            if sim > SIM_THRESH:
                # merge
                # print('xxxx merging xxxx')
                # print('\t', goods[-1])
                # print('\t', timeline[i])
                goods[-1][1] = timeline[i][1]
                goods[-1][2] = t_this
            else:
                goods.append(timeline[i])
            continue
        # rule-3:
        # 1 abcdef
        # 2 def
        # 上一行包含本行，合并两行，取上一行文本
        if len(t_last) > len(t_this):
            sim = calc_similary(t_last[-len(t_this):], t_this)
            if sim > SIM_THRESH:
                # print('xxxx merging xxxx')
                # print('\t', goods[-1])
                # print('\t', timeline[i])
                goods[-1][1] = timeline[i][1]
            else:
                goods.append(timeline[i])
            continue
        # rule-4:
        # 1 abcdef
        # 2 abcdxf
        # 两行相似则合并，取最长或后面的文本
        sim = calc_similary(t_last, t_this)
        if sim > SIM_THRESH:
            # print('xxxx merging xxxx')
            # print('\t', goods[-1])
            # print('\t', timeline[i])
            goods[-1][1] = timeline[i][1]
            if len(t_this) >= len(t_last):
                goods[-1][2] = t_this
        else:
            goods.append(timeline[i])
    return goods


def align_file(f_speech, f_subtitle, save_to):
    speeches = read_list(f_speech)
    subtitles = read_list(f_subtitle)
    goods, bads = align_them(speeches, subtitles)
    if not goods:
        return goods
    goods = align_merge(goods)
    f_goods = save_to + '.goods'
    save_list(goods, f_goods)
    f_bads = save_to + '.bads'
    save_list(bads, f_bads)
    return goods


def cut(audio_file, subtitles, save_format='wav'):
    '''subtitles: [(start, end, text), (start, end, text), ...]
    start: start of audio segment in miliseconds
    end: end of audio segment in miliseconds
    '''
    data, samplerate = librosa.load(audio_file, sr=16000, res_type="soxr_vhq")
    wav_scp = []
    trans = []
    dirname = os.path.dirname(audio_file)
    audio_subdir = os.path.join(dirname, save_format)
    if not os.path.exists(audio_subdir):
        os.makedirs(audio_subdir)
    hashid = audio_file.split('/')[-1].split('.')[0]
    for tl in subtitles:
        start = int(tl[0] / 1000 * samplerate)
        end = int(tl[1] / 1000 * samplerate)
        text = tl[2]
        utterance_id = f'{hashid}_{tl[0]}-{tl[1]}'
        # with open(text_path, 'w') as f:
        #     f.write(text)
        segment = data[start: end]
        fp_audio = os.path.join(audio_subdir, f'{utterance_id}.{save_format}')
        sf.write(fp_audio, segment, samplerate, format=save_format)
        wav_scp.append(f'{utterance_id}\t{fp_audio}\n')
        trans.append(f'{utterance_id}\t{text}\n')
    f_wav_scp = os.path.join(dirname, f'{hashid}-wav_scp.txt')
    with open(f_wav_scp, 'w') as f:
        f.write(''.join(wav_scp))
    f_trans = os.path.join(dirname, f'{hashid}-trans.txt')
    with open(f_trans, 'w') as f:
        f.write(''.join(trans))
    return wav_scp, trans


def align_all(worker, total):
    root_dir = '/aidata/audio/private/'
    # f_wav_scp = open(f'{root_dir}/wav_scp.txt', 'w')
    # f_trans = open(f'{root_dir}/trans.txt', 'w')
    suffix_speeches = '-speeches-raw.txt'
    suffix_subtitle = '-subtitle-raw.txt'
    counter = 0
    for root, dirs, files in os.walk(root_dir):
        for f in files:
            if not f.endswith(suffix_speeches):
                continue
            counter += 1
            hashid = f.split('-')[0]
            if int(hashid) % total != worker:
                continue
            f_speech = os.path.join(root, f)
            f_trans_this = os.path.join(root, f'{hashid}-trans.txt')
            if os.path.exists(f_trans_this):
                print('this done', f_speech)
                continue
            f_subtitle = f_speech.replace(suffix_speeches, suffix_subtitle)
            save_to = os.path.join(root, f'{hashid}-aligned.txt')
            goods = align_file(f_speech, f_subtitle, save_to)
            if not goods:
                print('bad:', f_subtitle)
                continue
            f_audio = f_speech.replace(suffix_speeches, '.opus')
            print(f'cutting {counter=}, {f_audio}')
            wav_scp, trans = cut(f_audio, goods, 'wav')
            # f_wav_scp.write(''.join(wav_scp))
            # f_wav_scp.flush()
            # f_trans.write(''.join(trans))
            # f_trans.flush()


if __name__ == '__main__':
    import sys
    worker = int(sys.argv[1])
    total = int(sys.argv[2])
    align_all(worker, total)
    # fs = sys.argv[1]
    # ft = sys.argv[2]
    # save_to = 'zznew'
    # align_file(fs, ft, save_to)
