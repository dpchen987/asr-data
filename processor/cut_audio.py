#!/usr/bin/env python3

import soundfile as sf
import librosa
import numpy as np


def cut(audio_file, timeline, save_format='wav'):
    '''timeline: [(start, end), (start, end), ...]
    start: start of audio segment in miliseconds
    end: end of audio segment in miliseconds
    '''
    data, samplerate = librosa.load(audio_file)
    print(data.shape, type(data), samplerate)
    counter = 0
    for tl in timeline:
        start = int(tl[0] / 1000 * samplerate)
        end = int(tl[1] / 1000 * samplerate)
        segment = data[start: end]
        save_name = audio_file + f'_{counter:05}.{save_format}'
        sf.write(save_name, segment, samplerate, format=save_format)
        counter += 1


def read_list(file_path):
    items = []
    with open(file_path) as f:
        for line in f:
            zz = line.strip().split('\t')
            item = [int(i) if i.isdigit() else i for i in zz]
            items.append(item)
    return items


if __name__ == '__main__':
    from sys import argv
    vf = argv[1]
    audio_file = vf + '.opus'
    timeline_file = vf + '-timeline.txt'
    tl = read_list(timeline_file)
    cut(audio_file, tl)