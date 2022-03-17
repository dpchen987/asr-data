#!/usr/bin/env python3

import sys
import soundfile as sf
print(sf.__libsndfile_version__)
fp = sys.argv[1]
# print(sf._libname)
# print(sf.available_formats())
# print(sf.available_subtypes())
# print(sf.available_subtypes('OGG'))

# data, samplerate = sf.read('z.opus')
data, samplerate = sf.read(fp)
print(samplerate)
print(len(data))
print('====')
print('====')
# data, samplerate = sf.read('9.mp3')
# # data, samplerate = sf.read('9.opus')
# print(samplerate)
# print(len(data))
# sf.write('abcjfe.opus', data, samplerate, subtype='opus', format='ogg')
# sf.write('abcjfe.mp3', data, samplerate, subtype='mp3', format='mpeg')
# sf.write('abcjfe.wav', data, samplerate, format='wav')

