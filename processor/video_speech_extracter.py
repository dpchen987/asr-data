import os

from video_subtitle_extracter import extract_subtitle
from video_subtitle_extracter import save_list
from video_subtitle_extracter import calc_similary, SIM_THRESH
from video_subtitle_extracter import fix_timeline
from gpvad.forward import GPVAD

GPVAD = GPVAD()


def get_audio(video_path, audio_path, channel=1, samplerate=48000, bitrate=32000):
    args = [
        f'-ac {channel}',
        f'-ar {samplerate}',
        f'-ab {bitrate}',
        '-y',
    ]
    supported_format = {
        'wav': '-map_metadata -1 -fflags +bitexact -acodec pcm_s16le',
        'opus': '-acodec libopus',
        'mp3': '-acodec libmp3lame',
    } 
    format = audio_path.split('.')[-1].lower()
    if format not in supported_format:
        raise ValueError(f'not supported audio format: {format}')
    args.append(supported_format[format])
    args = ' '.join(args)
    cmd = f'ffmpeg -i {video_path} {args} {audio_path}'
    print(cmd)
    os.system(cmd)


def merge_speeches(speeches):
    '''把极短的音频合并'''
    merged = [speeches[0]]
    min_duration = 1000  # ms
    min_gap = 110  # ms
    i = 0
    while i < len(speeches) - 1:
        i += 1
        if speeches[i][0] - merged[-1][1] < min_gap:
            merged[-1][1] = speeches[i][1]
            continue
        duration = speeches[i][1] - speeches[i][0]
        if duration < min_duration:
            merged[-1][1] = speeches[i][1]
            continue
        merged.append(speeches[i])
    return merged


def extract_speech(video_path, save_dir, audio_format='opus'):
    audio_name = video_path.split('/')[-1].replace('mp4', audio_format)
    audio_path = os.path.join(save_dir, audio_name) 
    get_audio(video_path, audio_path, samplerate=16000)
    assert os.path.exists(audio_path)
    speeches = GPVAD.vad(audio_path)
    return speeches


def align0(speeches, subtitles):
    alignments = []
    i = 0  # index of speeches
    j = 0  # index of subtitles
    gap_speech_subtitle = 300
    while i < len(speeches):
        print(i, speeches[i], '==', j, subtitles[j])
        speech_start, speech_end = speeches[i]
        # 先跳到跟本段语音重合的字幕
        while j < len(subtitles) - 1 and speech_start > subtitles[j][1]:
            j += 1
            continue
        sub_start = subtitles[j][0]
        sub_end = subtitles[j][1]
        if sub_start > speech_end or sub_end < speech_start:
            # 没有重合区域，skip 本段 speech
            print('\tskiped:', speech_start, speech_end, sub_start, sub_end)
            i += 1
            continue
        # 把语音范围内的字幕合并
        if abs(speech_start - sub_start) < gap_speech_subtitle:
            tl_start = min(speech_start, sub_start)
        else:
            tl_start = speech_start
        texts = [subtitles[j][2]]
        while j < len(subtitles) - 1 and speech_end >= subtitles[j][1]:
            j += 1
            texts.append(subtitles[j][2])
        if subtitles[j][0] > speech_end:
            j -= 1
            texts = texts[:-1]
        if abs(speech_end - subtitles[j][1]) < gap_speech_subtitle:
            tl_end = max(speech_end, subtitles[j][1])
        else:
            tl_end = speech_end
        text = ''.join(texts)
        if alignments and alignments[-1][2].endswith(text):
            alignments[-1][1] = tl_end
        else:
            alignments.append([tl_start, tl_end, ''.join(texts)])
        i += 1
    return alignments


def align_raw(speeches, subtitles):
    ''' raw subtitles: [(timestamp, text), ...]
    '''
    alignments = []
    i = 0  # index of speeches
    j = 0  # index of subtitles
    gap_speech_subtitle = 500
    for i, spch in enumerate(speeches):
        speech_start, speech_end = spch
        # 先跳到跟本段语音重合的字幕
        skiped_subs = []
        while j < len(subtitles) - 1 and (speech_start > subtitles[j][0] or not subtitles[j][1]):
            skiped_subs.append(subtitles[j])
            print('zzzzzz', j, len(subtitles))
            j += 1
            continue
        if j >= len(subtitles):
            continue
        print('-->', i, spch, '==>', j, subtitles[j])
        sub_stamp = subtitles[j][0]
        if sub_stamp < speech_start or sub_stamp > speech_end:
            # 没有重合区域，skip 本段 speech
            print('\tskiped:', speech_start, speech_end, sub_stamp)
            continue
        # 把语音范围内的字幕合并
        if skiped_subs:
            # 看看当前字幕与skip的是否相同，若同把speech_start回退到相同的
            for s in reversed(skiped_subs):
                sim = calc_similary(subtitles[j][1], s[1])
                if sim < SIM_THRESH:
                    break
                if abs(s[0] - speech_start) < gap_speech_subtitle:
                    speech_start = s[0]
                else:
                    break
        tl_start = speech_start
        sub_current = []
        while j < len(subtitles) and subtitles[j][0] <= speech_end:
            sub_current.append(subtitles[j])
            j += 1
        if not sub_current:
            print('\tno subtitle for speech:', i, spch)
            continue
        repeat_belong_to = ''
        if i < len(speeches) - 1:
            # 看下一个字幕是否和texts最后一个相同
            j_next = j
            next_sim_subs = []
            while j_next < len(subtitles):
                sim = calc_similary(sub_current[-1][1], subtitles[j_next][1])
                # print(sim, sub_current[-1][1], subtitles[j_next][1])
                if sim < SIM_THRESH:
                    break
                next_sim_subs.append(subtitles[j_next])
                j_next += 1
            # print('next_sum_subs:', next_sim_subs)
            if next_sim_subs:
                # 从后往前找sub_current 相同的字幕
                current_sim_subs = [sub_current[-1]]
                x = -2
                while x >= 0 - len(sub_current):
                    sim = calc_similary(sub_current[-1][1], sub_current[x][1])
                    if sim < SIM_THRESH:
                        break
                    current_sim_subs.append(sub_current[x])
                    x -= 1
                # 判断重复的字幕术语当前语音还是下一个
                print('\t000 i:', i, 'current_sim_subs:', current_sim_subs)
                time_current = speech_end - current_sim_subs[-1][0]
                speech_start_next = speeches[i+1][0]
                time_next = next_sim_subs[-1][0] - speech_start_next
                print('\t==', i, time_current, time_next)
                if time_current >= time_next:
                    # 属于当前语音
                    j = min(j_next, len(subtitles) - 1)
                    repeat_belong_to = 'current'
                    # print('==== j is ', j)
                else:
                    # 属于下一个语音
                    print('xxxx', x, sub_current)
                    sub_current = sub_current[:x+1]
                    repeat_belong_to = 'next'
                    # 当前重复的字幕放到下个语音对齐, 故j回退
                    print('\tvvvvvvv j back,', j, len(current_sim_subs))
                    j = j - len(current_sim_subs)
        if sub_current and abs(speech_end - sub_current[-1][0]) < gap_speech_subtitle:
            tl_end = max(speech_end, sub_current[-1][0])
        else:
            tl_end = speech_end
        tl_end = speech_end
        # print(f'{sub_current=}')
        sub_current = fix_timeline(sub_current)
        text = ''.join([s[2] for s in sub_current])
        # if alignments and alignments[-1][2].endswith(text):
        #     alignments[-1][1] = tl_end
        # else:
        #     alignments.append([tl_start, tl_end, text])
        if not text and repeat_belong_to == 'next':
            # 当前只有重复的还属于下一个，那么把本段视频合并到下一个
            speeches[i+1][0] = speech_start
        else:
            alignments.append([tl_start, tl_end, text])
    return alignments


def extract_align(video_path, save_dir):
    vp = video_path.replace('.mp4', '')
    subtitles = extract_subtitle(video_path, save_dir, fix=False)
    speeches = extract_speech(video_path, save_dir)
    video_name = video_path.split('/')[-1].replace('.mp4', '')
    save_list(speeches, os.path.join(save_dir, video_name+'-speeches-raw.txt'))
    speeches = merge_speeches(speeches)
    save_list(speeches, os.path.join(save_dir, video_name+'-speeches-merged.txt'))
    timeline = align_raw(speeches, subtitles)
    print(timeline)
    save_list(timeline, os.path.join(save_dir, video_name+'-timeline.txt'))
    return timeline


if __name__ == '__main__':
    from sys import argv
    from cut_audio import cut
    opt = argv[1]
    if opt == 'vad':
        ap = argv[2]
        tl = GPVAD.vad(ap)
        print(tl)
        cut(ap, tl)
    elif opt == 'sp':
        vp = argv[2]
        stl = extract_speech(vp, '.')
        print(stl)
    elif opt == 'ext':
        vp = argv[2]
        timeline = extract_align(vp)
        audio_file = vp.replace('mp4', 'wav')
        cut(audio_file, timeline)
    elif opt == 'alg':
        vp = argv[2]
        from video_subtitle_extracter import read_list
        subtitles = read_list(vp+'-subtitle-raw.txt')
        for s in subtitles:
            if len(s) == 1:
                s.append('')
        speeches = read_list(vp+'-speeches-raw.txt')
        speeches = merge_speeches(speeches)
        save_list(speeches, vp+'-speeches-merged.txt')
        timeline = align_raw(speeches, subtitles)
        #print(timeline)
        save_list(timeline, vp+'-timeline.txt')
        audio_file = vp + '.wav'
        cut(audio_file, timeline)
    else:
        print('invalid opt:', opt)
