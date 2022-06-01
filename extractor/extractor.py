#!/usr/bin/env python
# coding:utf-8

import os

from video_subtitle_extractor import extract_subtitle
from video_speech_extractor import extract_speech
import align_speech_subtitle as align
import utils


def timeline_to_scp_cut(audio_file, timeline, save_format='wav'):
    import librosa
    import soundfile as sf
    '''timeline: [(start, end, text), (start, end, text), ...]
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
    hashid = utils.get_hashid(audio_file)
    for tl in timeline:
        start = int(tl[0] / 1000 * samplerate)
        end = int(tl[1] / 1000 * samplerate)
        text = tl[2]
        utterance_id = f'{hashid}_{tl[0]}-{tl[1]}'
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


def timeline_to_scp(audio_file, timeline):
    wav_scp = []
    trans = []
    segments = []
    dirname = os.path.dirname(audio_file)
    hashid = utils.get_hashid(audio_file)
    for tl in timeline:
        text = tl[2]
        utterance_id = f'{hashid}_{tl[0]}-{tl[1]}'
        wav_scp.append(f'{utterance_id}\t{audio_file}\n')
        trans.append(f'{utterance_id}\t{text}\n')
        segments.append(f'{utterance_id}\t{utterance_id}\t{tl[0]}\t{tl[1]}\n')
    f_wav_scp = os.path.join(dirname, f'{hashid}-wav_scp.txt')
    with open(f_wav_scp, 'w') as f:
        f.write(''.join(wav_scp))
    f_trans = os.path.join(dirname, f'{hashid}-trans.txt')
    with open(f_trans, 'w') as f:
        f.write(''.join(trans))
    f_segments = os.path.join(dirname, f'{hashid}-segments.txt')
    with open(f_segments, 'w') as f:
        f.write(''.join(segments))


def extract(video_path, save_dir, audio_format, cut=False):
    # 1: extract speech
    speeches, audio_path = extract_speech(video_path, save_dir, audio_format)
    video_name = utils.get_name(video_path)
    path_speech = os.path.join(save_dir, f'{video_name}-speeches-raw.txt')
    utils.save_list(speeches, path_speech)
    # 2: extract subtitle
    subtitles = extract_subtitle(video_path, save_dir)
    path_subtitle = os.path.join(save_dir, f'{video_name}-subtitles-raw.txt')
    utils.save_list(subtitles, path_subtitle)
    # 3: align speech and subtitle
    timeline = align.align(speeches, subtitles)
    path_timeline = os.path.join(save_dir, f'{video_name}-timeline.txt')
    utils.save_list(timeline, path_timeline)
    # 4: convert timeline to wav_scp and trans text
    if cut:
        timeline_to_scp_cut(audio_path, timeline)
    else:
        timeline_to_scp(audio_path, timeline)
    return timeline



