#!/bin/bash

model_dir="tts_models"


echo "start downloading TTS models ..."
mkdir -p ${model_dir}
# ${model_dir} pretrained tts models and unzip
wget -P ${model_dir} https://paddlespeech.bj.bcebos.com/Parakeet/released_models/pwgan/pwg_aishell3_ckpt_0.5.zip
unzip -d ${model_dir} ${model_dir}/pwg_aishell3_ckpt_0.5.zip
wget -P ${model_dir} https://paddlespeech.bj.bcebos.com/Parakeet/released_models/fastspeech2/fastspeech2_nosil_aishell3_ckpt_0.4.zip
unzip -d ${model_dir} ${model_dir}/fastspeech2_nosil_aishell3_ckpt_0.4.zip
wget https://paddlespeech.bj.bcebos.com/Parakeet/tools/nltk_data.tar.gz
tar zxf nltk_data.tar.gz
echo "downloading models done"
echo "====== To know how to TTS, please run: ========"
echo "python tts_gen.py --help"
python tts_gen.py --help
