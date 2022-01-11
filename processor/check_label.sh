#!/bin/bash 
# --wav_scp  记录每个ID的音频文件路径:
# 		ID path_to_wav
# --text     记录每个ID的文本内容:
# 		ID text_of_speech
#
./label_checker_main --text segments.text --wav_scp segments.wav.scp --result z-result.txt --timestamp z-timestamp.txt --model_path /home/vee/projects/wenet-demo/models/final.zip --dict_path /home/vee/projects/wenet-demo/models/words.txt
