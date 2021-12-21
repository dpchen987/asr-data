#!/usr/bin/env python3

import os
import pickle
import re
import time
import cv2
import numpy as np
from paddleocr import PaddleOCR
import difflib
import contextlib
import wave


OCR = PaddleOCR(lang='ch')
differ = difflib.SequenceMatcher(isjunk=lambda x: x==' ')


def calc_width_height_ratio(box):
    width = box[1][0] - box[0][0]
    height = box[3][1] - box[0][1]
    ratio = width / height
    return ratio 


def calc_subtitle_score(box):
    '''rules:
    s = 1 * (width / height)
    '''
    score = 1 * calc_width_height_ratio(box)
    return score


def can_merge(last, this, height_threshold=5, y_threshold=5, x_threshold=5):
    # print('xxxxxxxxxxxxxxxxxxxx')
    # print('\tlast:', last)
    # print('\tthis:', this)
    last_height = last[3][1] - last[0][1]
    this_height = this[3][1] - this[0][1]
    if abs(last_height - this_height) > height_threshold:
        #print('\theight_fail', this, last_height, this_height)
        return 0 
    y_delta = abs(last[0][1] - this[0][1])
    if y_delta > y_threshold:
        #print('\ty fail', this, y_delta)
        return 0 
    # x gap 是前一句的结尾与后一句的开始之间的距离（应该小于一个字体宽度/高度）
    x_gap1 = abs(last[1][0] - this[0][0])
    x_gap2 = abs(this[1][0] - last[0][0]) 
    x_gap = min(x_gap1, x_gap2)
    if x_gap > (last_height + this_height) / 2:
        #print('\tx fail', this, x_gap)
        return 0 
    if x_gap1 < x_gap2:
        return 1  # last 在前
    else:
        return 2  # this 在前


def find_best(candidates, frame):
    ''' 方法：
    0. 合并位置Y差距小、位置X差距很小, 字体高度差距小的区域。有时候字幕断句间会加半个字体的宽度
    1. 宽高比要大
    2. 位置居中或居左（居右的没见过，是否有？）
    '''
    # r0.
    candidates.sort(key=lambda a: a[0][0])  # 按x从左到右排序
    merges = []
    merged_index = {}  # {candidates_index: merge_index}
    for i in range(len(candidates)):
        this = candidates[i]
        merge_index = len(merges)
        merge = [i]
        for j in range(i+1, len(candidates)):
            next = candidates[j]
            if can_merge(this, next):
                if j in merged_index:
                    merges[merged_index[j]].append(j)
                else:
                    merge.append(j)
                    merged_index[j] = merge_index
        if len(merge) > 1:
            merged_index[i] = merge_index
            merges.append(merge)
    #print('xxx', merges)
    #print('---', merged_index)
    has_merged = []
    for m in merges:
        xx_starts = min([candidates[i][0][0] for i in m])
        xx_ends = max([candidates[i][1][0] for i in m])
        yy_starts = min([candidates[i][0][1] for i in m])
        yy_ends = max([candidates[i][3][1] for i in m])
        #print(xx_starts, xx_ends, yy_starts, yy_ends)
        new = [
            [xx_starts, yy_starts],
            [xx_ends, yy_starts],
            [xx_ends, yy_ends],
            [xx_starts, yy_ends]
        ]
        #print('aaa', new)
        has_merged.append(new)
    for i in range(len(candidates)):
        if i not in merged_index:
            #print('bbb', candidates[i])
            has_merged.append(candidates[i])
    # r1.
    weights = []
    for box in has_merged:
        score = calc_subtitle_score(box)
        position = calc_position(box, frame)
        if position == 'right':
            score *= 0.5
        weights.append((box, position, score))
    weights.sort(key=lambda a: a[2], reverse=True)
    return weights[0][:2]
    

def small_it(frame, ):
    # return frame, 1, 0
    to_size_min = 450
    height, width, _ = frame.shape
    ratio = to_size_min / min(height, width)
    height = int(height * ratio)
    width = int(width * ratio)
    resized = cv2.resize(frame, (width, height), interpolation=cv2.INTER_NEAREST)
    # 截取下面部分检测字幕
    crop_ratio = 0.75
    start_x = int(height * crop_ratio)
    end_x = height
    start_y = 0
    end_y = width
    resized = resized[start_x:end_x, start_y:end_y]
    # print('resized:', resized.shape)
    return resized, ratio, crop_ratio


def calc_position(box, frame):
    '''
    box: box of text by OCR
    frame: the image has the box
    return: left, middle, right
    '''
    box_middle_x = (box[0][0] + box[1][0]) / 2
    middle = frame.shape[1] / 2
    delta = middle * 0.1
    if box_middle_x < middle - delta:
        return 'left'
    if box_middle_x > middle + delta: 
        return 'right'
    return 'middle'


def detect_subtitle(frame_origin):
    '''box:
    paddleOCR 的坐标是宽高：
        0,0: 左上角
        x: 宽度
        y: 高度
        [
            (top_left.x, top_left.y),
            (top_right.x, top_left.y),
            (bottom_right.x, bottom_right.y),
            (bottome_left.x, bottome_right.y)
        ]
        先把图片缩小：1. 主要是提高处理速度，2. 不影响字幕检查，或许可以屏蔽非字幕的检测
    '''
    frame_resized, ratio, crop_ratio = small_it(frame_origin)
    # b = time.time()
    boxes = OCR.ocr(frame_resized, det=True, rec=False, cls=False)
    # print('\tOCR.ocr detect', time.time() - b)
    # print('boxes:')
    # print(frame_origin.shape)
    height, width, _ = frame_resized.shape
    # print(f'{width=}, {height=}')
    candicates = []
    for b in boxes:
        if calc_width_height_ratio(b) < 1.5:
            # 字幕应该是X方向的长方形
            continue
        #if b[0][1] > position_threshold and b[1][1] > position_threshold:
        candicates.append(b)
    if not candicates:
        return None, '' 
    # print('candicates:', candicates)
    if len(candicates) == 1:
        box = candicates[0]
        position = calc_position(box, frame_resized)
    else:
        box, position = find_best(candicates, frame_resized)
    # print('---:', box)
    top_left, top_right, bottom_right, bottom_left = box
    crop_offset = int(frame_origin.shape[0] * crop_ratio)
    # opencv 的坐标是高宽：（0,0）：左上角，x：向下(高度), y: 向右(宽度)
    # OpenCV的xy是paddleOCR box的y,x， 故如下进行crop
    startY, endY = int((top_left[0] - 1) / ratio), int((top_right[0] + 1) / ratio)
    startX, endX = int((top_left[1] - 1) / ratio), int((bottom_left[1] + 1) / ratio)
    startX += crop_offset
    endX += crop_offset
    # print(startX, endX, startY, endY)
    sub = frame_origin[startX:endX, startY:endY, :]
    return sub, position


def find_end_start(subtitles, buffer, sub_position):
    '''skip的frame可能包含上一字幕和当前字幕，从buffer里面找到上一字幕的结尾和当前字幕的开始
    可能的buffer: [last, last, last, .., current, current, curent]
    '''
    left = 0
    right = len(buffer) - 1
    pos = len(buffer) // 2
    if subtitles:
        last_text = subtitles[-1][1]
    else:
        # 第一帧, subtitles 还是空的
        last_text = ''
    last_end = 0
    current_start = 0
    current_text = ''
    while 1:
        #print(f'{pos=}', len(buffer))
        ts, frame = buffer[pos]
        sub, position = detect_subtitle(frame)
        if sub is None or position != sub_position:
            text = ''
        else:
            texts = OCR.ocr(sub, det=False, rec=True, cls=False)
            texts = [t[0] for t in texts if t[1] > 0.8]
            text = text_normalize(''.join(texts))
        if text != last_text:
            # go left
            right = pos
            pos = (left + right) // 2
            current_start = ts
            current_text = text
        else:
            # go right
            left = pos
            pos = (left + right) // 2
            last_end = ts
        if pos == left or pos == right:
            break
    if last_end:
        print(f'\t{last_end=}, {last_text=}')
        subtitles.append((last_end, last_text))
    if current_start:
        print(f'\t{current_start=}, {current_text=}')
        subtitles.append((current_start, current_text))


def extract_subtitle(video_path):
    print('start extracting...')
    cap = cv2.VideoCapture(video_path)
    main_frame_subtitles = {}  #{frame_id: (timestamp, text, position), }
    fps = cap.get(cv2.CAP_PROP_FPS)
    # 跳过n帧以加速提取，find_end()从跳过的帧中找到变化位置，
    # 但其假设是n帧中字幕只变化了一次，故n不能过大，否则会漏掉时间很短的字幕
    skip_frame = fps
    # 第一次遍历video，识别main_frame(非skipped)，统计出视频位置：left/middle/right
    positions = {'left': 0, 'middle': 0, 'right': 0}
    i = 0
    while (cap.isOpened()):
        frame_exists, frame = cap.read()
        if not frame_exists:
            break
        i += 1
        if i % 1500 == 1:
            print('===frame:', i)
        if i % skip_frame != 1:
            continue
        sub, position = detect_subtitle(frame)
        current = int(cap.get(cv2.CAP_PROP_POS_MSEC))
        if sub is None:
            main_frame_subtitles[i] = (current, '', '')
            continue
        positions[position] += 1
        texts = OCR.ocr(sub, det=False, rec=True, cls=False)
        texts = [t[0] for t in texts if t[1] > 0.8]
        text = text_normalize(''.join(texts))
        main_frame_subtitles[i] = (current, text, position)
    cap.release()
    zz = sorted(positions.items(), key=lambda a: a[1], reverse=True)
    sub_position = zz[0][0]
    print('=== find sub_position:', sub_position, zz)
    # 第二次遍历，识别skip frame，找到更精确的字幕开始结束时间
    sim_thresh = 0.75
    buffer = []  # 缓存被skip掉的帧, [(timestamp, frame), ]
    subtitles = []  # [(timestamp, text), ]
    cap = cv2.VideoCapture(video_path)
    buffer = []
    i = 0
    while (cap.isOpened()):
        frame_exists, frame = cap.read()
        if not frame_exists:
            break
        i += 1
        current = int(cap.get(cv2.CAP_PROP_POS_MSEC))
        if i % skip_frame != 1:
            buffer.append((current, frame))
            continue
        ts, text, position = main_frame_subtitles[i]
        if position != sub_position:
            print('!!!!!', position, text)
            text = ''
        if not text and i == 1:
            continue
        if not text:
            find_end_start(subtitles, buffer, sub_position)
            buffer.clear()
            continue
        if not subtitles:
            find_end_start(subtitles, buffer, sub_position)
        elif calc_similary(text, subtitles[-1][1]) < sim_thresh:
            find_end_start(subtitles, buffer, sub_position)
        print(current, text)
        subtitles.append((current, text))
        buffer.clear()
    cap.release()
    return subtitles


def text_normalize(text):
    non_stop_puncs = '＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃《》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏'
    text = text.replace(' ', '')
    text = re.sub(non_stop_puncs, '', text)
    return text


def calc_similary(t1, t2):
    differ.set_seq1(t1)
    differ.set_seq2(t2)
    return differ.ratio()


def get_best(texts):
    if len(set(texts)) == 1:
        return texts[0]
    index = {}
    for t in texts:
        if t in index:
            index[t] += 1
        else:
            index[t] = 1
    items = [(i[0], i[1]*len(i[0])) for i in index.items()]
    items.sort(key=lambda a: a[1], reverse=True)
    return items[0][0]


def fix_timeline(subtitles):
    i = 0
    print('subtitles:', len(subtitles))
    sim_thresh = 0.75
    timelines = []
    while i < len(subtitles):
        texts = []
        start, text = subtitles[i]
        i += 1
        text = text_normalize(text)
        if not text:
            continue
        texts.append(text)
        end = start
        for j in range(i, len(subtitles)):
            i = j
            textj = text_normalize(subtitles[j][1])
            if calc_similary(textj, text) < sim_thresh:
                break
            texts.append(textj)
            end = subtitles[j][0]
        text = get_best(texts)
        # timelines.append([start, end, text])
        # continue
        if not timelines:
            timelines.append([start, end, text])
        elif calc_similary(text, timelines[-1][2]) > sim_thresh:
            timelines[-1][1] = end
            if len(text) > len(timelines[-1][2]):
                timelines[-1][2] = text
        else:
            timelines.append([start, end, text])
    return timelines


def save_list(list_data, file_path):
    with open(file_path, 'w') as f:
        for t in list_data:
            z = [str(i) for i in t]
            s = "\t".join(z)
            line = f'{s}\n'
            f.write(line)
    

def extract_timeline(video_path):
    b = time.time()
    subtitles = extract_subtitle(video_path)
    save_list(subtitles, 'z-timeline-raw.txt')
    with open('z-subtitles.pickle', 'wb') as f:
        pickle.dump(subtitles, f)
    timeline = fix_timeline(subtitles)
    save_list(timeline, 'z-timeline.txt')
    print('done', time.time() - b)
    return timeline

# ===== audio processing =============

def get_audio(video_path, audio_path):
    cmd = f'ffmpeg -i {video_path} -map_metadata -1 -fflags +bitexact -acodec pcm_s16le -ac 1 -ar 16000 {audio_path} -y'
    os.system(cmd)


def read_wave(path):
    """Reads a .wav file.

    Takes the path, and returns (PCM audio data, sample rate).
    """
    with contextlib.closing(wave.open(path, 'rb')) as wf:
        num_channels = wf.getnchannels()
        assert num_channels == 1
        sample_width = wf.getsampwidth()
        assert sample_width == 2
        sample_rate = wf.getframerate()
        assert sample_rate in (8000, 16000, 32000, 48000)
        pcm_data = wf.readframes(wf.getnframes())
        return pcm_data, sample_rate


def write_wave(path, audio, sample_rate):
    """Writes a .wav file.

    Takes path, PCM audio data, and sample rate.
    """
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)


def cut_audio(audio_path, timeline, save_dir):
    audio, sample_rate = read_wave(audio_path)
    frame_duration_ms = 20  # 20 ms of one audio frame
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    print('==== n ', n, len(audio), len(audio)/n * frame_duration_ms)
    last_end = 0
    padding = 20  # padding 20ms before start, after end
    i = 0
    for start, end, text in timeline:
        if not text or start == end:
            continue
        if start > last_end:
            start -= padding
        last_end = end
        end -= padding
        n_start = int(start / frame_duration_ms * n)
        n_end = int(end / frame_duration_ms * n) + 2
        chunk = audio[n_start:n_end]
        i += 1
        save_audio_path = os.path.join(save_dir, f'{i:05}.wav')
        save_text_path = os.path.join(save_dir, f'{i:05}.txt')
        write_wave(save_audio_path, chunk, sample_rate)
        with open(save_text_path, 'w') as f:
            f.write(text)
    

def extract_speech_text(video_path, save_dir):
    timeline = extract_timeline(video_path)
    # audio_path = f'{video_path}.wav'
    audio_path = 'tmp-process.wav'
    get_audio(video_path, audio_path)
    cut_audio(audio_path, timeline, save_dir)
    

if __name__ == '__main__':
    from sys import argv
    opt = argv[1]
    if opt == 'det':
        fn = argv[2]
        img = cv2.imread(fn)
        b = time.time()
        sub, pos = detect_subtitle(img)
        print('detect ', time.time() - b)
        print('position:', pos)
        b = time.time()
        text = OCR.ocr(sub, det=False, rec=True, cls=False)
        print('recognize:', time.time() - b, text)
        cv2.imwrite('z-sub.jpg', sub)
        print()
    elif opt == 'tl':
        fn = argv[2]
        timeline = extract_timeline(fn)
    elif opt == 'fix':
        subtitles = pickle.load(open('z-subtitles.pickle', 'rb'))
        tl = fix_timeline(subtitles)
        save_list(tl, 'zz.txt')
    elif opt == 'cut':
        fn = argv[2]
        timeline = []
        with open('z-timeline.txt') as f:
            for l in f:
                zz = l.strip().split()
                if len(zz) != 3:
                    print('invalid ', l)
                    continue
                z = (int(zz[0]), int(zz[1]), zz[2])
                timeline.append(z)
        cut_audio(fn, timeline, 'segments')
    elif opt == 'ext':
        fn = argv[2]
        save_dir = 'segments'
        extract_speech_text(fn, save_dir)
    else:
        print('nothing')
