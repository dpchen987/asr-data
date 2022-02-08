#!/usr/bin/env python3

import os
import pickle
import re
import time
import copy
from collections import Counter
import numpy as np
import cv2
import numpy as np
from paddleocr import PaddleOCR

from utils import text_normalize, calc_similary, save_list


RESIZE_RATIO = 1.0
CROP_HEIGHT_RATIO = 0.75
SIM_THRESH = 0.80  # 对OCR容错

print(f'================== CPU:{os.cpu_count()} ================')
OCR = PaddleOCR(
    lang='ch',
    # cpu_threads=,  #  40 比默认的10 还慢一点点
    enable_mkldnn=True,
)


def small_it(frame,):
    # return frame, 1, 0
    # to_size_min = 500
    height, width, _ = frame.shape
    # resize_ratio = to_size_min / min(height, width)
    height = int(height * RESIZE_RATIO)
    width = int(width * RESIZE_RATIO)
    resized = cv2.resize(frame, (width, height), interpolation=cv2.INTER_NEAREST)
    # 截取下面部分检测字幕
    start_x = int(height * CROP_HEIGHT_RATIO)
    end_x = height
    start_y = 0
    end_y = width
    resized = resized[start_x:end_x, start_y:end_y]
    # print('resized:', resized.shape)
    return resized


def calc_side(box, frame):
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


def crop_origin_sub(box, resize_ratio, crop_height_ratio, frame_origin):
    # print('---:', box)
    top_left, top_right, bottom_right, bottom_left = box
    crop_offset = int(frame_origin.shape[0] * crop_height_ratio)
    # opencv 的坐标是高宽：（0,0）：左上角，x：向下(高度), y: 向右(宽度)
    # OpenCV的xy是paddleOCR box的y,x， 故如下进行crop
    startY, endY = int((top_left[0] - 1) / resize_ratio), int((top_right[0] + 1) / resize_ratio)
    startX, endX = int((top_left[1] - 1) / resize_ratio), int((bottom_left[1] + 1) / resize_ratio)
    startX += crop_offset
    endX += crop_offset
    # print(startX, endX, startY, endY)
    sub = frame_origin[startX:endX, startY:endY, :]
    return sub


def get_main_sub(subs, sub_statistic):
    candidates = []
    delta = sub_statistic['sub_font_height'] * 0.5  # pixels
    for b in subs:
        if abs(b['sub_y_start'] - sub_statistic['sub_y_start']) > delta:
            # print(f"{b['sub_y_position']=}, {sub_statistic['sub_y_position']=}, {delta=}")
            continue
        if abs(b['sub_font_height'] - sub_statistic['sub_font_height']) > delta:
            # print(f"{b['sub_y_height']=}, {sub_statistic['sub_y_height']=}, {delta=}")
            continue
        if b['sub_side'] != sub_statistic['sub_side'] and b['sub_side'] != 'middle':
            continue
        candidates.append(b['sub_box'])
    if not candidates:
        # print('\tno candidates of subs', len(subs))
        return None
    # print('has candidates:', len(candidates))
    if len(candidates) == 1:
        box = candidates[0]
    else:
        # 符合条件的多个boxes应该是一行中间用空格隔开的，需要merge为一个
        candidates.sort(key=lambda a: a[0][0])
        box = [
            candidates[0][0],
            candidates[-1][1],
            candidates[-1][2],
            candidates[0][3]
        ]
    return box


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
    frame_resized = small_it(frame_origin)
    # b = time.time()
    boxes = OCR.ocr(frame_resized, det=True, rec=False, cls=False)
    if not boxes:
        return None
    result = []
    for b in boxes:
        sub_side = calc_side(b, frame_resized)
        sub_font_height = b[3][1] - b[0][1]
        result.append({
            'sub_box': b,
            'sub_side': sub_side,
            'sub_y_start': b[0][1],
            'sub_font_height': sub_font_height,
        })
    return result

    
def find_end_start(subtitles, buffer, sub_statistic):
    '''skip的frame可能包含上一字幕和当前字幕，从buffer里面找到上一字幕的结尾和当前字幕的开始
    可能的buffer: [last, last, last, .., current, current, curent]
    '''
    if not buffer:
        return
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
        subs = detect_subtitle(frame)
        if subs is None:
            text = ''
        else:
            sub_box = get_main_sub(subs, sub_statistic)
            if sub_box is None:
                text = ''
            else:
                sub_img = crop_origin_sub(
                    sub_box,
                    RESIZE_RATIO,
                    CROP_HEIGHT_RATIO,
                    frame)
                texts = OCR.ocr(sub_img, det=False, rec=True, cls=False)
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


def find_subtitle_area(areas):
    grouped = set()
    groups = []
    for i in range(len(areas)):
        if i in grouped:
            continue
        grouped.add(i)
        a = areas[i]
        group = [a]
        for j in range(i+1, len(areas)):
            if j in grouped:
                continue
            b = areas[j]
            if ((abs(a[0] - b[0]) < a[2]*0.5) and
                (abs(a[1] - b[1]) < a[2]*0.5) and
                (abs(a[2] - b[2]) < a[2]*0.3)):
                group.append(b)
                grouped.add(j)
        groups.append(group)
    # 取x_end变化最多的group
    print('grous:', len(groups))
    group_count = {}
    for i, group in enumerate(groups):
        count = 0
        print('\tgrous:', len(group), i)
        for j in range(1, len(group)):
            if abs(group[j][3] - group[j-1][3]) >= 1 * group[j][2]:
                # x end 差值大于1个字高
                count += 1
        group_count[i] = count
    zz = sorted(group_count.items(), key=lambda a: a[1], reverse=True)
    idx = zz[0][0]
    print('xxx', group_count, idx)
    best = groups[idx]
    return best
    

def subtitle_statistic(main_frame_subtitles):
    '''字幕区域：高度不变，x长度不断变化
    输出： 字幕区域的高度以及字体的高度
    '''
    areas = []
    for k, v in main_frame_subtitles.items():
        if v[1] is None:
            continue
        for sub in v[1]:
            s = sub['sub_box']
            # print(s, type(s))
            x_start, y_start = s[0]
            x_end = s[1][0]
            sub_side = sub['sub_side']
            areas.append((x_start, y_start, sub['sub_font_height'], x_end, k, sub_side))
    best = find_subtitle_area(areas)
    sides = [s[-1] for s in best]
    print(sides)
    ct = Counter(sides)
    side = ct.most_common(1)[0][0]
    zz = [[b[0], b[1], b[2]] for b in best]
    x_start, y_start, font_height = np.mean(zz, axis=0)
    return {
        'sub_side': side,
        'sub_x_start': x_start,
        'sub_y_start': y_start,
        'sub_font_height': font_height,
    }
 

def extract_subtitle_raw(video_path):
    print('start extracting...')
    cap = cv2.VideoCapture(video_path)
    main_frame_subtitles = {}  #{frame_id: (timestamp, None or [sub, sub, ...]), }
    fps = cap.get(cv2.CAP_PROP_FPS)
    # 跳过n帧以加速提取，find_end()从跳过的帧中找到变化位置，
    # 但其假设是n帧中字幕只变化了一次，故n不能过大，否则会漏掉时间很短的字幕
    skip_frame = int(fps)
    # 第一次遍历video，识别main_frame(非skipped)，然后统计出视频位置：left/middle/right, 高度、高度位置
    i = 0
    while (cap.isOpened()):
        frame_exists, frame = cap.read()
        if not frame_exists:
            break
        i += 1
        if i % 1500 == 1:
            print(f'===frame: {i} @skip_frame:{skip_frame}, fps: {fps}', time.ctime())
        if i % skip_frame != 1:
            continue
        subs = detect_subtitle(frame)
        current = int(cap.get(cv2.CAP_PROP_POS_MSEC))
        main_frame_subtitles[i] = (current, subs)
    cap.release()
    sub_statistic = subtitle_statistic(main_frame_subtitles)
    print('=== sub_statistic:', sub_statistic)
    # 第二次遍历，识别skip frame，找到更精确的字幕开始结束时间
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
        print(f'frame: {i}')
        ts, subs = main_frame_subtitles[i]
        if subs is None:
            text = ''
        else:
            sub_box = get_main_sub(subs, sub_statistic)
            if sub_box is None:
                text = ''
            else:
                sub_img = crop_origin_sub(
                    sub_box,
                    RESIZE_RATIO,
                    CROP_HEIGHT_RATIO,
                    frame)
                texts = OCR.ocr(sub_img, det=False, rec=True, cls=False)
                texts = [t[0] for t in texts if t[1] > 0.7]
                text = text_normalize(''.join(texts))
        if not text and i == 1:
            continue
        if not text:
            find_end_start(subtitles, buffer, sub_statistic)
            buffer.clear()
            continue
        if not subtitles:
            find_end_start(subtitles, buffer, sub_statistic)
        elif calc_similary(text, subtitles[-1][1]) < SIM_THRESH:
            find_end_start(subtitles, buffer, sub_statistic)
        print(current, text)
        subtitles.append((current, text))
        buffer.clear()
    cap.release()
    return subtitles


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
            if calc_similary(textj, text) < SIM_THRESH:
                break
            texts.append(textj)
            end = subtitles[j][0]
        text = get_best(texts)
        # timelines.append([start, end, text])
        # continue
        if not timelines:
            timelines.append([start, end, text])
        elif calc_similary(text, timelines[-1][2]) > SIM_THRESH:
            timelines[-1][1] = end
            if len(text) > len(timelines[-1][2]):
                timelines[-1][2] = text
        else:
            # if timelines and start - timelines[-1][1] > 1000:
            #     print(timelines[-1], start)
            #     timelines[-1][1] += min(2000, int(2*(start-timelines[-1][1])/3))
            timelines.append([start, end, text])
    return timelines


def merge_timeline(timeline):
    '''把间隔小于n秒的字幕合并为同一条，以避免字幕、声音不同步
    '''
    timeline.sort(key=lambda a: a[0])
    thresh = 200
    groups = []
    group = [timeline[0]]
    for i in range(1, len(timeline)):
        delta = timeline[i][0] - group[-1][1]
        if delta < thresh:
            print('\t', delta, i, len(groups))
            group.append(timeline[i])
        else:
            print('==== new group', delta, i, len(groups))
            groups.append(copy.deepcopy(group))
            group = [timeline[i]]
    merged = []
    for g in groups:
        print('g:', g)
        text = ''.join([t[2] for t in g])
        m = (g[0][0], g[-1][1], text)
        merged.append(m)
    return merged


def extract_subtitle(video_path, save=True, fix=True):
    b = time.time()
    subtitles = extract_subtitle_raw(video_path)
    # with open(f'{video_name}-subtitles.pickle', 'wb') as f:
    #     pickle.dump(subtitles, f)
    timeline_fixed = fix_timeline(subtitles)
    if save:
        video_name = video_path.replace('.mp4', '')
        save_list(subtitles, f'{video_name}-subtitle-raw.txt')
        save_list(timeline_fixed, f'{video_name}-subtitle.txt')
    # timeline = merge_timeline(timeline)
    # save_list(timeline, f'{video_name}-timeline-merged.txt')
    print('done', time.time() - b)
    if fix:
        return timeline_fixed
    return subtitles

   
if __name__ == '__main__':
    from sys import argv
    opt = argv[1]
    if opt == 'det':
        fn = argv[2]
        img = cv2.imread(fn)
        b = time.time()
        text = OCR.ocr(img, det=True, rec=True, cls=False)
        print('recognize:', time.time() - b, text)
        print(text)
    elif opt == 'fix':
        subtitles = pickle.load(open('z-subtitles.pickle', 'rb'))
        tl = fix_timeline(subtitles)
        save_list(tl, 'z-timeline.txt')
    else:
        print('nothing')
