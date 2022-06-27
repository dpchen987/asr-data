#!/usr/bin/env python
# coding:utf-8


import re
import os


def findfiles(idir, postfix):
    allfiles = {}  # {name: path}
    for root, dirs, files in os.walk(idir):
        for f in files:
            if not f.endswith(postfix):
                print('bad', f, root)
                continue
            path = os.path.join(root, f)
            allfiles[f] = path
    print(f'{idir} has {len(allfiles)=}')
    return allfiles


def main2():
    processed = findfiles('/aidisk/audio/private2', '.mp3')
    videos = findfiles('/aidata/video/电视剧2-9/', '.mp4')

    done = set()
    for mp3 in processed:
        hashid = mp3.split('.')[0]
        done.add(hashid)

    left_videos = set()
    for mp4 in videos:
        hashid = mp4.split('.')[0]
        if hashid in done:
            continue
        left_videos.add(hashid)
    print(f'{len(left_videos)=}')


def main():
    processed = findfiles('/aidisk/audio/private2', '.mp3')
    videos = findfiles('/aidata/video/电视剧2-9/', '.mp4')

    names = {}
    for mp3 in processed:
        mp4 = mp3.replace('.mp3', '.mp4')
        if mp4 not in videos:
            # print('bad', mp4)
            continue
        video_path = videos[mp4]
        name = video_path.split('电视剧2/')[-1].split('/')[0]
        if name in names:
            names[name] += 1
        else:
            names[name] = 1
    from pprint import pprint
    zz = sorted(names.items(), key=lambda a: a[1], reverse=True)
    pprint(zz)
    print(f'{len(zz)=}\n')
    # print(' '.join([z[0] for z in zz]))
    left = {}
    for mp4, video_path in videos.items():
        # print(video_path)
        name = video_path.split('电视剧2-9/')[-1].split('/')[0]
        # print('name', name)
        if name in names:
            continue
        if name in left:
            left[name] += 1
        else:
            left[name] = 1
    zz = sorted(left.items(), key=lambda a: a[1], reverse=True)
    pprint(zz)
    print('\n')
    print(' '.join([z[0] for z in zz]))
    print('left', sum([z[1] for z in zz]))

main2()
