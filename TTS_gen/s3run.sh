#!/bin/bash
source path.sh

gpus=0
stage=0
stop_stage=100

# with the following command, you can choice the stage range you want to run
# such as `./run.sh --stage 0 --stop-stage 0`
# this can not be mixed use with `$1`, `$2` ...
echo ${MAIN_ROOT}
source ${MAIN_ROOT}/asr/utils/parse_options.sh || exit 1

mkdir -p download

if [ ${stage} -le 0 ] && [ ${stop_stage} -ge 0 ]; then
    # download pretrained tts models and unzip
    wget -P download https://paddlespeech.bj.bcebos.com/Parakeet/released_models/pwgan/pwg_aishell3_ckpt_0.5.zip
    unzip -d download download/pwg_aishell3_ckpt_0.5.zip
    wget -P download https://paddlespeech.bj.bcebos.com/Parakeet/released_models/fastspeech2/fastspeech2_nosil_aishell3_ckpt_0.4.zip
    unzip -d download download/fastspeech2_nosil_aishell3_ckpt_0.4.zip
fi

if [ ${stage} -le 1 ] && [ ${stop_stage} -ge 1 ]; then
    # run tts
    CUDA_VISIBLE_DEVICES=${gpus} \
    python3 tts_mp.py \
        --fastspeech2-config=/home/dapeng/download/fastspeech2_nosil_aishell3_ckpt_0.4/default.yaml \
        --fastspeech2-checkpoint=/home/dapeng/download/fastspeech2_nosil_aishell3_ckpt_0.4/snapshot_iter_96400.pdz \
        --fastspeech2-stat=/home/dapeng/download/fastspeech2_nosil_aishell3_ckpt_0.4/speech_stats.npy \
        --pwg-config=/home/dapeng/download/pwg_aishell3_ckpt_0.5/default.yaml \
        --pwg-checkpoint=/home/dapeng/download/pwg_aishell3_ckpt_0.5/snapshot_iter_1000000.pdz \
        --pwg-stat=/home/dapeng/download/pwg_aishell3_ckpt_0.5/feats_stats.npy \
        --text=/home/dapeng/asr/style_fs2/item_kw.txt \
        --output-dir=/aidata/audio/tts_keywd \
        --phones-dict=/home/dapeng/download/fastspeech2_nosil_aishell3_ckpt_0.4/phone_id_map.txt \
        --speaker-dict=/home/dapeng/download/fastspeech2_nosil_aishell3_ckpt_0.4/speaker_id_map.txt
fi
