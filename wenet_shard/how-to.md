# wenet shard data

这是 wenet UIO 使用的数据结构，把一定数量（比如1000个）的语音文件及其文本打包成tar文件，以便在训练过程中快速加载数据。

# 工具

wenet 提供了制作shard的工具： wenet/tools/make_shard_list.py 。

# 输入

该工具的输入是kalid数据格式，及两个文件：

* wav_scp.txt : 每行一条数据如下：
    * utterance_id path-to-wav
* trans.txt: 每行一条数据如下：
    * utterance_id text-of-wav

**注意**  文本需要nomalization，使用 `textnorm_zh.py`

有些数据把很多条音频合并为一个音频文件保存，提供 segemnts.txt 文件记录每个utterance的时间offset，格式如下：

```
utterance_id utterance_id start end
```

虽然该工具支持segments，但我们制作数据时，不做成segments，而是一条语音一个文件的方式。

# 输出

该工具把生成的tar包写在某个目录下，同时把tar文件的路径记录在一个list文件（一行一个tar文件路径）, 故其输出是：

* path-to-tar-dir
* file-of-tar-list

# 例子：

假设，我们有`dev`, `test`, `train` 三类数据，要制作成shard数据：

```bash
#!/bin/bash
shard_dir=/aidata/audio/private/shards-1
for datatype in dev test train;
do
    trans_norm=$datatype-trans.txt.norm
    ./textnorm_zh.py --to_lower --has_key $datatype-trans.txt $trans_norm
    ./make_shard_list.py --resample 16000 --num_utts_per_shard 1000 --num_threads 32 \
        ./$datatype-wav_scp.txt ./$trans_norm \
        $shard_dir/$datatype $shards_dir/$datatype-shards_list
done

# wenet 训练需要两类数据：train-data, cv-data, 故：
cat shards_/dev-shards_list shards_new/test-shards_list >> shards/cv-shards_list
```
