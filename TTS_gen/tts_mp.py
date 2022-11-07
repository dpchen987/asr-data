# Copyright (c) 2021 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse, random
from pathlib import Path

import numpy as np
import paddle
import soundfile as sf
import yaml
from yacs.config import CfgNode

from paddlespeech.t2s.frontend.zh_frontend import Frontend
from paddlespeech.t2s.models.fastspeech2 import FastSpeech2
from paddlespeech.t2s.models.fastspeech2 import StyleFastSpeech2Inference
from paddlespeech.t2s.models.parallel_wavegan import PWGGenerator
from paddlespeech.t2s.models.parallel_wavegan import PWGInference
from paddlespeech.t2s.modules.normalizer import ZScore
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

def evaluate(args, fastspeech2_config, pwg_config, lines, mp_lk, sent_num):

    # construct dataset for evaluation
#     sentences = []
#     with open(args.text, 'rt') as f:
#         for line in f:
#             items = line.strip().split()
#             utt_id = items[0]
#             sentence = "".join(items[1:])
#             sentences.append((utt_id, sentence))
#     print("in process")
    with open(args.phones_dict, "r") as f:
        phn_id = [line.strip().split() for line in f.readlines()]
    vocab_size = len(phn_id)
    print("vocab_size:", vocab_size)
    
    with open(args.speaker_dict, "r") as f:
        spk_ids = [line.strip().split() for line in f.readlines()]
    spk_num = len(spk_ids)
    print("spk_num:", spk_num)

    odim = fastspeech2_config.n_mels
    model = FastSpeech2(
        idim=vocab_size, spk_num=spk_num, odim=odim, **fastspeech2_config["model"])

    model.set_state_dict(
        paddle.load(args.fastspeech2_checkpoint)["main_params"])
    model.eval()

    vocoder = PWGGenerator(**pwg_config["generator_params"])
    vocoder.set_state_dict(paddle.load(args.pwg_checkpoint)["generator_params"])
    vocoder.remove_weight_norm()
    vocoder.eval()
    print("model done!")

    frontend = Frontend(phone_vocab_path=args.phones_dict)
    print("frontend done!")

    stat = np.load(args.fastspeech2_stat)
    mu, std = stat
    mu = paddle.to_tensor(mu)
    std = paddle.to_tensor(std)
    fastspeech2_normalizer = ZScore(mu, std)

    stat = np.load(args.pwg_stat)
    mu, std = stat
    mu = paddle.to_tensor(mu)
    std = paddle.to_tensor(std)
    pwg_normalizer = ZScore(mu, std)

    fastspeech2_inference = StyleFastSpeech2Inference(
        fastspeech2_normalizer, model, args.fastspeech2_pitch_stat,
        args.fastspeech2_energy_stat)
    fastspeech2_inference.eval()

    pwg_inference = PWGInference(pwg_normalizer, vocoder)
    pwg_inference.eval()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    train_wav_dir = output_dir / f"wavs/train/t{sent_num // 10000:0>2d}/t{sent_num // 100:0>4d}" 
    train_wav_dir.mkdir(parents=True, exist_ok=True)
    test_wav_dir = output_dir / f"wavs/test/ts{sent_num // 10000:0>2d}" 
    test_wav_dir.mkdir(parents=True, exist_ok=True)
    dev_wav_dir = output_dir / f"wavs/dev/d{sent_num // 10000:0>2d}" 
    dev_wav_dir.mkdir(parents=True, exist_ok=True)
    train_scp_dir = output_dir / f"transcript/train" 
    train_scp_dir.mkdir(parents=True, exist_ok=True)
    test_scp_dir = output_dir / f"transcript/test" 
    test_scp_dir.mkdir(parents=True, exist_ok=True)
    dev_scp_dir = output_dir / f"transcript/dev" 
    dev_scp_dir.mkdir(parents=True, exist_ok=True)
#     styles = ["normal", "1.2xspeed", "0.8xspeed", "1.3pitch", "0.7pitch", "1.3energy", "0.7energy", "spk10", "spk100"]
#     for spk_id in sorted(random.sample(range(spk_num),100)):
#     for style in styles:
    if True:
        durations = None
        durations_scale = None
        durations_bias = None
        pitch = None
        pitch_scale = None
        pitch_bias = None
        energy = None
        energy_scale = None
        energy_bias = None
#         spk_emb=None,
        
    styles = ["spd10", "spd12", "spd08"]
        
#         sub_output_dir = output_dir / style
    output_dir.mkdir(parents=True, exist_ok=True)
#     for utt_id, sentence in sentences:
    t2t_pth = str(train_scp_dir / "tts_trans.txt")
    s2t_pth = str(train_scp_dir / "tts_wav_scp.txt")
    t2d_pth = str(dev_scp_dir / "tts_dev_trans.txt")
    s2d_pth = str(dev_scp_dir / "tts_dev_wav_scp.txt")
    t2ts_pth = str(test_scp_dir / "tts_test_trans.txt")
    s2ts_pth = str(test_scp_dir / "tts_test_wav_scp.txt")
    
    with open(t2t_pth, "a", encoding="utf8") as t2t_f, open(s2t_pth, "a", encoding="utf8") as s2t_f, open(t2d_pth, "a", encoding="utf8") as t2d_f, open(s2d_pth, "a", encoding="utf8") as s2d_f, open(t2ts_pth, "a", encoding="utf8") as t2ts_f, open(s2ts_pth, "a", encoding="utf8") as s2ts_f, paddle.no_grad():
        stop_num = 0
        cnt_tr = 0
        cnt_de = 0
        cnt_ts = 0
        for line in lines:
#             stop_num += 1
#             if stop_num >10: break
            utt_id, sentence = line.strip().split()
            input_ids = frontend.get_input_ids(sentence, merge_sentences=True)
            phone_ids = input_ids["phone_ids"][0]
#             print(f"--------{phone_ids}")
            for spk_id in sorted(random.sample(range(spk_num),10)):
    #             选取不同的speakers
    #             spk_id=spk_id
                style = random.choice(styles)
                if style == "spd12": durations_scale = 1 / 1.1
                elif style == "spd08": durations_scale = 1 / 0.9
                else: durations_scale = 1
                aud_name = f"{utt_id}spk{spk_id:0>3d}{style}"
#                 with paddle.no_grad():
                mel = fastspeech2_inference(
                    phone_ids,
                    durations=durations,
                    durations_scale=durations_scale,
                    durations_bias=durations_bias,
                    pitch=pitch,
                    pitch_scale=pitch_scale,
                    pitch_bias=pitch_bias,
                    energy=energy,
                    energy_scale=energy_scale,
                    energy_bias=energy_bias,
#                     spk_emb=spk_emb,
                    spk_id=paddle.to_tensor(spk_id))
                wav = pwg_inference(mel)

#                 sf.write(
#                     str(output_wav_dir / (aud_name + ".wav")),
#                     wav.numpy(),
#                     samplerate=fastspeech2_config.fs)
#                 wav_url = str(output_wav_dir / (aud_name + ".wav"))        
                mp_lk.acquire()
                rand_ch = random.random()
                if rand_ch < 0.98:
                    wav_url = str(train_wav_dir / (aud_name + ".wav"))       
                    sf.write(wav_url, wav.numpy(), samplerate=fastspeech2_config.fs)
                    t2t_f.write(f"{aud_name}\t{sentence}\n")
                    s2t_f.write(f"{aud_name}\t{wav_url}\n")
                    cnt_tr += 1
                    if cnt_tr >= 20:
                        cnt_tr = 0
                        t2t_f.flush()
                        s2t_f.flush()
                elif rand_ch > 0.99:
                    wav_url = str(dev_wav_dir / (aud_name + ".wav"))       
                    sf.write(wav_url, wav.numpy(), samplerate=fastspeech2_config.fs)
                    t2d_f.write(f"{aud_name}\t{sentence}\n")
                    s2d_f.write(f"{aud_name}\t{wav_url}\n") 
                    cnt_de += 1
                    if cnt_de >= 20:
                        cnt_de = 0
                        t2d_f.flush()
                        s2d_f.flush()
                else:
                    wav_url = str(test_wav_dir / (aud_name + ".wav"))       
                    sf.write(wav_url, wav.numpy(), samplerate=fastspeech2_config.fs)
                    t2ts_f.write(f"{aud_name}\t{sentence}\n")
                    s2ts_f.write(f"{aud_name}\t{wav_url}\n") 
                    cnt_ts += 1
                    if cnt_ts >= 20:
                        cnt_ts = 0
                        t2ts_f.flush()
                        s2ts_f.flush()
                mp_lk.release()
            print(f"{utt_id} {sentence} done!")
                              
def main():
    # parse args and config and redirect to train_sp
    parser = argparse.ArgumentParser(
        description="Synthesize with fastspeech2 & parallel wavegan.")
    parser.add_argument(
        "--fastspeech2-config", type=str, help="fastspeech2 config file.")
    parser.add_argument(
        "--fastspeech2-checkpoint",
        type=str,
        help="fastspeech2 checkpoint to load.")
    parser.add_argument(
        "--fastspeech2-stat",
        type=str,
        help="mean and standard deviation used to normalize spectrogram when training fastspeech2."
    )
    parser.add_argument(
        "--fastspeech2-pitch-stat",
        type=str,
        help="mean and standard deviation used to normalize pitch when training fastspeech2"
    )
    parser.add_argument(
        "--fastspeech2-energy-stat",
        type=str,
        help="mean and standard deviation used to normalize energy when training fastspeech2."
    )
    parser.add_argument(
        "--pwg-config", type=str, help="parallel wavegan config file.")
    parser.add_argument(
        "--pwg-checkpoint",
        type=str,
        help="parallel wavegan generator parameters to load.")
    parser.add_argument(
        "--pwg-stat",
        type=str,
        help="mean and standard deviation used to normalize spectrogram when training parallel wavegan."
    )
    parser.add_argument(
        "--phones-dict",
        type=str,
        default="phone_id_map.txt",
        help="phone vocabulary file.")
#     speaker-dict aishell3
    parser.add_argument(
        "--speaker-dict",
        type=str,
        default="speaker_id_map.txt",
        help="speaker vocabulary file.")
    
    parser.add_argument(
        "--text",
        type=str,
        help="text to synthesize, a 'utt_id sentence' pair per line.")
    parser.add_argument("--output-dir", type=str, help="output dir.")
    parser.add_argument(
        "--ngpu", type=int, default=0, help="if ngpu == 0, use cpu.")
    parser.add_argument("--verbose", type=int, default=1, help="verbose.")

    args = parser.parse_args()

    if args.ngpu == 0:
        paddle.set_device("cpu")
    elif args.ngpu > 0:
        paddle.set_device("gpu")
    else:
        print("ngpu should >= 0 !")

    with open(args.fastspeech2_config) as f:
        fastspeech2_config = CfgNode(yaml.safe_load(f))
    with open(args.pwg_config) as f:
        pwg_config = CfgNode(yaml.safe_load(f))

    print("========Args========")
    print(yaml.safe_dump(vars(args)))
    print("========Config========")
    print(fastspeech2_config)
    print(pwg_config)
    m = multiprocessing.Manager()
    mp_lk = m.Lock()
#     mp_lk = multiprocessing.Lock()
    mp_bitch = 100
    with open(args.text, 'rt', encoding="utf8", errors="ignore") as f, ProcessPoolExecutor(max_workers=16) as ppl:
        lines = []
        sent_num = 0
        for line in f:
            sent_num += 1
#             if sent_num < 500000: continue
            lines.append(line)
            
#            if sent_num >165: break
            if len(lines) >= mp_bitch:
                ppl.submit(evaluate, args, fastspeech2_config, pwg_config, lines, mp_lk, sent_num)
                print(f"##{sent_num}lines")
                lines = []
        if len(lines) >= 0:
            ppl.submit(evaluate, args, fastspeech2_config, pwg_config, lines, mp_lk, sent_num)


if __name__ == "__main__":
    main()
