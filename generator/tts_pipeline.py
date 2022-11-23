#!/usr/bin/env python3
# coding:utf-8

import os
import random
import soundfile as sf
import soxr
from pathlib import Path
import numpy as np
import paddle
import yaml
from yacs.config import CfgNode
from paddlespeech.t2s.models.fastspeech2 import FastSpeech2
from paddlespeech.t2s.models.fastspeech2 import FastSpeech2Inference
from paddlespeech.t2s.modules.normalizer import ZScore
from paddlespeech.t2s.models.parallel_wavegan import PWGGenerator
from paddlespeech.t2s.models.parallel_wavegan import PWGInference
from paddlespeech.t2s.frontend.zh_frontend import Frontend


class TTSPipeline:
    def __init__(self, model_dir):
        print('loading acoustic_model ...')
        self.acoustic_model, self.frontend = self.load_acoustic(model_dir)
        print('loading vocoder ...')
        self.vocoder = self.load_vocoder(model_dir)
        if os.environ.get('CUDA_VISIBLE_DEVICES'):
            gpu_id = os.environ.get('CUDA_VISIBLE_DEVICES')
            gpu_id = f'gpu:{gpu_id}'
            print(f'paddle.set_device to GPU: {gpu_id = }')
            # paddle.set_device(gpu_id)
        else:
            print('paddle.set_device to CPU')
            paddle.set_device('cpu')

    def load_acoustic(self, model_dir):
        # 加载预训练模型
        model_dir = Path(model_dir)
        checkpoint_dir = model_dir / "fastspeech2_nosil_aishell3_ckpt_0.4"
        with open(checkpoint_dir / "phone_id_map.txt", "r") as f:
            phn_id = [line.strip().split() for line in f.readlines()]
        vocab_size = len(phn_id)
        with open(checkpoint_dir / "default.yaml") as f:
            fastspeech2_config = CfgNode(yaml.safe_load(f))
        self.samplerate = fastspeech2_config['fs']
        odim = fastspeech2_config.n_mels
        with open(checkpoint_dir / "speaker_id_map.txt") as f:
            spk_ids = [line.strip().split() for line in f]
        spk_num = len(spk_ids)
        self.spk_num = spk_num
        print(f'{self.samplerate = }, {spk_num = }')
        model = FastSpeech2(
            idim=vocab_size, spk_num=spk_num,
            odim=odim, **fastspeech2_config["model"])
        path = (checkpoint_dir / "snapshot_iter_96400.pdz").as_posix()
        model.set_state_dict(
            paddle.load(path)["main_params"])
        model.eval()
        # 加载特征文件
        stat = np.load(checkpoint_dir / "speech_stats.npy")
        mu, std = stat
        mu = paddle.to_tensor(mu)
        std = paddle.to_tensor(std)
        fastspeech2_normalizer = ZScore(mu, std)
        # 构建预测对象
        fastspeech2_inference = FastSpeech2Inference(
                fastspeech2_normalizer, model)
        fastspeech2_normalizer.eval()
        # load Chinese Frontend
        frontend = Frontend(
                phone_vocab_path=checkpoint_dir / "phone_id_map.txt")
        return fastspeech2_inference, frontend

    def load_vocoder(self, model_dir):
        # 加载预训练模型
        model_dir = Path(model_dir)
        checkpoint_dir = model_dir / "pwg_aishell3_ckpt_0.5"
        with open(checkpoint_dir / "default.yaml") as f:
            pwg_config = CfgNode(yaml.safe_load(f))
        vocoder = PWGGenerator(**pwg_config["generator_params"])
        path = (checkpoint_dir / "snapshot_iter_1000000.pdz").as_posix()
        vocoder.set_state_dict(
                paddle.load(path)["generator_params"])
        vocoder.remove_weight_norm()
        vocoder.eval()
        # 加载特征文件
        stat = np.load(checkpoint_dir / "feats_stats.npy")
        mu, std = stat
        mu = paddle.to_tensor(mu)
        std = paddle.to_tensor(std)
        pwg_normalizer = ZScore(mu, std)
        # 加载预训练模型构造预测对象
        pwg_inference = PWGInference(pwg_normalizer, vocoder)
        pwg_inference.eval()
        return pwg_inference

    def tts(self, sentence, save_as, speakers=1, resample=16000):
        input_ids = self.frontend.get_input_ids(sentence, merge_sentences=True)
        phone_ids = input_ids["phone_ids"][0]
        # 构建预测对象加载中文前端，对中文文本前端的输出进行分段
        wavs = []
        with paddle.no_grad():
            for spk_id in random.sample(range(self.spk_num), speakers):
                path = f'{save_as}_{spk_id:0>3}.wav'
                uttid = path.split('/')[-1]
                wavs.append((uttid, sentence, path))
                if os.path.exists(path):
                    # print(f'has {path}, skip gen')
                    continue
                mel = self.acoustic_model(
                        phone_ids, spk_id=paddle.to_tensor(spk_id))
                wav = self.vocoder(mel)
                if resample != self.samplerate:
                    wav = soxr.resample(wav, self.samplerate, resample)
                    samplerate = resample
                else:
                    samplerate = self.samplerate
                sf.write(path, wav, samplerate=samplerate)
        return wavs


if __name__ == '__main__':
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    pl = TTSPipeline('./tts_models')
    sentence = '重不重，轻不轻啊'
    sentence = '重不重轻不轻啊'
    wav = pl.tts(sentence, 'zz.wav', 5)
