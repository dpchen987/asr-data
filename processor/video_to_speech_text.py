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
import difflib
import contextlib
import wave


RESIZE_RATIO = 0.7
CROP_HEIGHT_RATIO = 0.75
SIM_THRESH = 0.80  # 对OCR容错

OCR = PaddleOCR(lang='ch')
differ = difflib.SequenceMatcher(isjunk=lambda x: x==' ')


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


def get_most_mean(data, delta):
    data.sort()
    result = []
    group = [data[0]]
    i = 1
    while i < len(data):
        delta = group[-1] * 0.3
        if data[i] - group[-1] < delta:
            group.append(data[i])
        else:
            result.append(group.copy())
            group = [data[i]]
        i += 1
    if group:
        result.append(group)
    result.sort(key=lambda a: len(a), reverse=True)
    mean = int(sum(result[0]) / len(result[0]))
    # print(result)
    # print('most: ', len(result[0]), 'mean:', mean, 'groups:', len(result), 'total:', len(data))
    return mean


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
 

def is_sub_box(sub_feature, sub):
    sub = sub['sub_box']
    # print('isisisisisisis', unchanged_subs)
    # print(sub)
    y_position = int(sub[0][1])
    font_height = int((sub[3][1] - sub[0][1]))
    if abs(y_position - sub_feature[1]) < sub_feature[2] * 0.5 and abs(font_height - sub_feature[2]) < sub_feature[2]*0.3:
        return True
    return False
 

def extract_subtitle(video_path):
    print('start extracting...')
    cap = cv2.VideoCapture(video_path)
    main_frame_subtitles = {}  #{frame_id: (timestamp, None or [sub, sub, ...]), }
    fps = cap.get(cv2.CAP_PROP_FPS)
    # 跳过n帧以加速提取，find_end()从跳过的帧中找到变化位置，
    # 但其假设是n帧中字幕只变化了一次，故n不能过大，否则会漏掉时间很短的字幕
    skip_frame = fps
    # 第一次遍历video，识别main_frame(非skipped)，然后统计出视频位置：left/middle/right, 高度、高度位置
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
    video_name = video_path.split('/')[-1]
    save_list(subtitles, f'{video_name}-timeline-raw.txt')
    with open(f'{video_name}-subtitles.pickle', 'wb') as f:
        pickle.dump(subtitles, f)
    timeline = fix_timeline(subtitles)
    save_list(timeline, f'{video_name}-timeline.txt')
    # timeline = merge_timeline(timeline)
    # save_list(timeline, f'{video_name}-timeline-merged.txt')
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
    
def fix_timeline_with_audio(audio_path, timeline):
    from pydub import AudioSegment, silence
    audio = AudioSegment.from_wav(audio_path)
    sounds = silence.detect_nonsilent(audio, min_silence_len=30, silence_thresh=audio.dBFS)
    print('timelines: {}, sounds: {}'.format(len(timeline), len(sounds)))
    fixed = []
    i = 0  # index of timeline
    j = 0  # index of sounds
    while i < len(timeline):
        tl_start = timeline[i][0]
        tl_end = timeline[i][1]
        if fixed and tl_start < fixed[-1][0]:
            fixed[-1][1] = tl_end
            fixed[-1][2] += timeline[i][2]
            i += 1
            continue
        print(timeline[i])
        while j < len(sounds):
            print('\tsounds:', sounds[j])
            if tl_start > sounds[j][1]:
                j += 1
                continue
            if tl_end < sounds[j][0]:
                break
            tl_start = min(tl_start, sounds[j][0])
            tl_end = max(tl_end, sounds[j][1])
            break
        fixed.append([tl_start, tl_end, timeline[i][2]])
        i += 1
    return fixed
    

def extract_speech_text(video_path, save_dir):
    timeline = extract_timeline(video_path)
    # audio_path = f'{video_path}.wav'
    audio_path = f'{video_path}.wav'
    get_audio(video_path, audio_path)
    cut_audio(audio_path, timeline, save_dir)
    

if __name__ == '__main__':
    def read(tl_name):
        timeline = []
        with open(tl_name) as f:
            for l in f:
                zz = l.strip().split()
                if len(zz) != 3:
                    print('invalid ', l)
                    continue
                z = [int(zz[0]), int(zz[1]), zz[2]]
                timeline.append(z)
        return timeline
        
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
        save_list(tl, 'z-timeline.txt')
    elif opt == 'cut':
        audio_file = argv[2]
        video_file = argv[3].split('/')[-1]
        tl_name = f'{video_file}-timeline.txt'
        print(tl_name)
        timeline = read(tl_name)
        timeline = merge_timeline(timeline)
        save_list(timeline, f'{video_file}-timeline-merged.txt')
        cut_audio(audio_file, timeline, 'segments')
    elif opt == 'ext':
        fn = argv[2]
        save_dir = 'segments'
        extract_speech_text(fn, save_dir)
    elif opt == 't':
        print('fix.....')
        audio_file = argv[2]
        video_file = argv[3]
        tl_name = f'{video_file}-timeline.txt'
        timeline = read(tl_name)
        tl = fix_timeline_with_audio(audio_file, timeline)
        with open(f'{tl_name}.fixed', 'w') as f:
            for t in tl:
                line = f'{t[0]}\t{t[1]}\t{t[2]}\n'
                f.write(line)
        cut_audio(audio_file, tl, 'segments')
    else:
        print('nothing')
