import os
import time

import utils
from logger import logger

VAD = None


def extract_speech(video_path, save_dir, audio_format):
    global VAD
    b = time.time()
    audio_name = utils.get_name(video_path)
    audio_path = os.path.join(save_dir, f'{audio_name}.{audio_format}')
    if not os.path.exists(audio_path):
        utils.get_audio(video_path, audio_path)
    assert os.path.exists(audio_path)
    if VAD is None:
        from gpvad.forward import GPVAD
        VAD = GPVAD()
    speeches = VAD.vad(audio_path)
    span = time.time() - b
    logger.info(f'done extract audio: {audio_path}, time cost:{span}')
    return speeches, audio_path


if __name__ == '__main__':
    from sys import argv
    opt = argv[1]
    if opt == 'sp':
        vp = argv[2]
        stl, ap = extract_speech(vp, '.', 'mp3')
        print(stl)
        print(len(stl))
        print(ap)
    else:
        print('invalid opt:', opt)
