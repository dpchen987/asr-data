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
