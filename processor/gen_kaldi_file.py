#!/usr/bin/env python3

import os


def gen(segments_dir):
    wav_scp = []
    text = []
    for root, dirs, files in os.walk(segments_dir):
        for f in files:
            if f.endswith('.wav'):
                p = f.rfind('.wav')
                utt_id = f[:p]
                wav_path = os.path.join(root, f)
                wav_scp.append(f'{utt_id} {wav_path}')
                text_path = os.path.join(root, utt_id+'.txt')
                with open(text_path) as f:
                    content = f.read()
                text.append(f'{utt_id} {content}')
    segments_dir = segments_dir.strip('/')
    with open(f'{segments_dir}.wav.scp', 'w') as f:
        f.write('\n'.join(wav_scp))
    with open(f'{segments_dir}.text', 'w') as f:
        f.write('\n'.join(text))
    print('done')


if __name__ == '__main__':
    from sys import argv
    fd = argv[1]
    gen(fd)

