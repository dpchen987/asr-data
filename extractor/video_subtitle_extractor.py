#!/usr/bin/env python3
# encoding: utf8

import os
import time
from collections import Counter
import numpy as np
import cv2
from utils import text_normalize, calc_similary
from logger import logger


CROP_HEIGHT_RATIO = 0.75
SIM_THRESH = 0.80  # 对OCR容错
too_small_thresh = 20
OCR = None


def init():
    from paddleocr import PaddleOCR
    global OCR
    logger.warn(f'================== CPU:{os.cpu_count()} ================')
    # import GPUtil
    # use_gpu = GPUtil.getGPUs()
    import paddle
    use_gpu = paddle.fluid.is_compiled_with_cuda()
    if use_gpu:
        logger.warn(f'=========== PaddleOCR using GPU {use_gpu} ============')
        OCR = PaddleOCR(
            lang='ch',
            use_gpu=True,
            gpu_mem=1000,
        )
    else:
        OCR = PaddleOCR(
            lang='ch',
            cpu_threads=8,  # 40 比默认的10 还慢一点点
            enable_mkldnn=True,
        )


def small_it(frame,):
    # return frame, 1, 0
    height, width, _ = frame.shape
    # 截取下面部分检测字幕
    start_y = int(height * CROP_HEIGHT_RATIO)
    end_y = height
    start_x = 0
    end_x = width
    resized = frame[start_y:end_y, start_x:end_x]
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


def crop_origin_sub(box, crop_height_ratio, frame_origin):
    top_left, top_right, bottom_right, bottom_left = box
    crop_offset = int(frame_origin.shape[0] * crop_height_ratio)
    startX, endX = int((top_left[0] - 1)), int((top_right[0] + 1))
    startY, endY = int((top_left[1] - 1)), int((bottom_left[1] + 1))
    startY += crop_offset
    endY += crop_offset
    sub = frame_origin[startY:endY, startX:endX, :]
    return sub


def get_main_sub(subs, sub_statistic):
    candidates = []
    delta = sub_statistic['sub_font_height'] * 0.5  # pixels
    for b in subs:
        if abs(b['sub_y_start'] - sub_statistic['sub_y_start']) > delta:
            continue
        if abs(b['sub_font_height'] - sub_statistic['sub_font_height']) > delta:
            continue
        if b['sub_side'] != sub_statistic['sub_side'] and b['sub_side'] != 'middle':
            continue
        candidates.append(b['sub_box'])
    if not candidates:
        return None
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
        sub_width = b[1][0] - b[0][0]
        sub_font_height = b[3][1] - b[0][1]
        if sub_width < sub_font_height * 2:
            # skip less than 2 char
            continue
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
    buffer_texts = []
    while 1:
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
                    CROP_HEIGHT_RATIO,
                    frame)
                if (sub_img.shape[0] < too_small_thresh or
                        sub_img.shape[1] < too_small_thresh):
                    text = ''
                else:
                    texts = OCR.ocr(sub_img, det=False, rec=True, cls=False)
                    texts = [t[0] for t in texts if t[1] > 0.6]
                    text = text_normalize(''.join(texts))
                    buffer_texts.append((ts, text))
        if text != last_text:
            # go left
            right = pos
            pos = (left + right) // 2
        else:
            # go right
            left = pos
            pos = (left + right) // 2
        if pos == left or pos == right:
            break
    if buffer_texts:
        buffer_texts.sort(key=lambda a: a[0])
        logger.debug(f'{buffer_texts=}')
        subtitles.extend(buffer_texts)


def find_subtitle_area(areas):
    grouped = set()
    groups = []
    for i in range(len(areas)):
        if i in grouped:
            continue
        grouped.add(i)
        a = areas[i]
        group = [a]
        half_height = a[2] * 0.5
        for j in range(i+1, len(areas)):
            if j in grouped:
                continue
            b = areas[j]
            if b[-1] == 'left':
                # 居左，则起点变化不大
                near_by = ((abs(a[0]-b[0]) < half_height) and
                        (abs(a[1]-b[1]) < half_height) and
                        (abs(a[2]-b[2]) < a[2]*0.3))
            elif b[-1] == 'middle':
                # 居中，则中点变化不大
                middle_a = (a[3] + a[0]) / 2
                middle_b = (b[3] + b[0]) / 2
                near_by = ((abs(middle_a-middle_b) < half_height) and
                        (abs(a[1]-b[1]) < half_height) and
                        (abs(a[2]-b[2]) < a[2]*0.3))
            else:
                # 居右，则尾点变化不大
                near_by = ((abs(a[3]-b[3]) < half_height) and
                        (abs(a[1]-b[1]) < half_height) and
                        (abs(a[2]-b[2]) < a[2]*0.3))
            if near_by:
                group.append(b)
                grouped.add(j)
        groups.append(group)
    # 取x_end变化最多的group
    group_count = {}
    for i, group in enumerate(groups):
        count = 0
        for j in range(1, len(group)):
            if abs(group[j][3] - group[j-1][3]) >= 1 * group[j][2]:
                # x end 差值大于1个字高
                count += 1
        group_count[i] = count
    zz = sorted(group_count.items(), key=lambda a: a[1], reverse=True)
    idx = zz[0][0]
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
            x_start, y_start = s[0]
            x_end = s[1][0]
            sub_side = sub['sub_side']
            areas.append((x_start, y_start, sub['sub_font_height'], x_end, k, sub_side))
    best = find_subtitle_area(areas)
    sides = [s[-1] for s in best]
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
    cap = cv2.VideoCapture(video_path)
    main_frame_subtitles = {}  # {frame_id: (timestamp, None or [sub, sub, ...]), }
    fps = cap.get(cv2.CAP_PROP_FPS)
    # 跳过n帧以加速提取，find_end()从跳过的帧中找到变化位置，
    # 但其假设是n帧中字幕只变化了一次，故n不能过大，否则会漏掉时间很短的字幕
    skip_frame = int(fps * 1.2)
    # 第一次遍历video，识别main_frame(非skipped)，然后统计出视频位置：left/middle/right, 高度、高度位置
    i = 0
    while (cap.isOpened()):
        frame_exists, frame = cap.read()
        if not frame_exists:
            break
        if i % 1500 == 0:
            now = time.ctime()
            logger.debug(f'===frame: {i} @{skip_frame=}, {fps=}, time: {now}')
        i += 1
        if i % skip_frame != 0:
            continue
        subs = detect_subtitle(frame)
        current = int(cap.get(cv2.CAP_PROP_POS_MSEC))
        main_frame_subtitles[i] = (current, subs)
    cap.release()
    sub_statistic = subtitle_statistic(main_frame_subtitles)
    logger.info(f'=== {sub_statistic=}')
    # 第二次遍历，识别skip frame，找到更精确的字幕开始结束时间
    buffer = []  # 缓存被skip掉的帧, [(timestamp, frame), ]
    subtitles = []  # [(timestamp, text), ]
    cap = cv2.VideoCapture(video_path)
    buffer = []
    i = 0
    last_frame_has_text = False
    while (cap.isOpened()):
        frame_exists, frame = cap.read()
        if not frame_exists:
            break
        i += 1
        current = int(cap.get(cv2.CAP_PROP_POS_MSEC))
        if i % skip_frame != 0:
            buffer.append((current, frame))
            continue
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
                    CROP_HEIGHT_RATIO,
                    frame)
                if sub_img.shape[0] < too_small_thresh or sub_img.shape[1] < too_small_thresh:
                    text = ''
                else:
                    texts = OCR.ocr(sub_img, det=False, rec=True, cls=False)
                    texts = [t[0] for t in texts if t[1] > 0.6]
                    text = text_normalize(''.join(texts))
        # if not text and i == 1:
        #     continue
        if not text:
            if last_frame_has_text:
                find_end_start(subtitles, buffer, sub_statistic)
            buffer.clear()
            last_frame_has_text = False
            continue
        if not subtitles:
            find_end_start(subtitles, buffer, sub_statistic)
        elif calc_similary(text, subtitles[-1][1]) < SIM_THRESH:
            find_end_start(subtitles, buffer, sub_statistic)
        logger.debug(f'frame:{i=}, {current=}, {text=}')
        subtitles.append((current, text))
        buffer.clear()
        last_frame_has_text = True
    cap.release()
    return subtitles


def extract_subtitle(video_path, save_dir):
    if OCR is None:
        init()
    b = time.time()
    subtitles = extract_subtitle_raw(video_path)
    logger.info(f'done extract_subtitle: {video_path}, time:{time.time() - b}')
    return subtitles


if __name__ == '__main__':
    from sys import argv
    opt = argv[1]
    if opt == 'det':
        fn = argv[2]
        img = cv2.imread(fn)
        init()
        bt = time.time()
        box = detect_subtitle(img)
        print('detect time:', time.time() - bt)
        bt = time.time()
        for b in box:
            print(b)
            im = crop_origin_sub(b['sub_box'], CROP_HEIGHT_RATIO, img)
            texts = OCR.ocr(im, det=False, rec=True, cls=False)
            texts = [t[0] for t in texts]
            print(''.join(texts), '\n\n')
        print('rec time:', time.time() - bt)
    elif opt == 'ext':
        vp = argv[2]
        save_dir = '.'
        subs = extract_subtitle(vp, save_dir)
        import utils
        utils.save_list(subs, 'z-ocr-.txt')
    else:
        print('nothing')
