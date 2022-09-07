import glob
import textgrid
from pydub import AudioSegment
import json

def merge_annotated(file_path):
    lii = glob.glob(file_path)      # wav file name

    # get txt for each file
    li = {}
    for j in lii:
        tg = textgrid.TextGrid(strict=0)
        tg.read(j)
        sub_li = {}
        for i in tg.tiers[0]:
            if i.mark != '':
                sub_li[str((i.minTime, i.maxTime))] = i.mark
        li[j] = sub_li

    # get each merge file length and source from
    k = 0
    res = []
    before = 0
    di = {}

    for j in lii:
        k += 1
        tg = textgrid.TextGrid(strict=0)
        tg.read(j)
        for i in tg.tiers[0]:
            if i.mark != '':
                time = i.maxTime - i.minTime + 1
                if before + time > 60:
                    res.append((before, di.copy()))
                    before = time
                    di = {}
                    di[j] = [(i.minTime, i.maxTime)]
                else:
                    before += time
                    if j in di.keys():
                        di[j].append((i.minTime, i.maxTime))
                    else:
                        di[j] = [(i.minTime, i.maxTime)]
    res.append((before, di))

    # merge audio and get corresponding text
    silence = AudioSegment.silent(duration=1000)
    txt = {}

    for i in range(len(res)):
        info = res[i]
        out_name = f'merge\\{i}.wav'
        combined = AudioSegment.empty()

        sub_txt = []
        time = 0

        for name in info[1].keys():
            cut_li = info[1][name]
            wav_name = name.replace('textgrid', 'wav')
            sound_file = AudioSegment.from_wav(wav_name)

            for j in cut_li:
                t = li[name][str(j)]
                if time == 0:
                    sub_txt.append([(0, j[1] - j[0]), t])
                    end = j[1] - j[0]
                else:
                    end = time + 1 + (j[1] - j[0])
                    sub_txt.append([(time + 1, end), t])
                time = end
                combined += sound_file[j[0] * 1000: j[1] * 1000]
                combined += silence
            file_handle = combined.export(out_name, format="wav")
            txt[f'{i}.wav'] = sub_txt

    with open("merge/text.json", "w", encoding='utf8') as outfile:
        json.dump(txt, outfile)