#!/usr/bin/env python
# coding:utf-8


def get_text(tar_file):
    import tarfile
    texts = []
    with tarfile.open(tar_file) as tar:
        for tarinfo in tar:
            if not tarinfo.name.endswith('.txt'):
                continue
            uttid, postfix = tarinfo.name.rsplit('.', maxsplit=1)
            with tar.extractfile(tarinfo) as file_obj:
                text = file_obj.read().decode('utf8')
            texts.append(f'{uttid}\t{text}\n')
    return texts


def main(shards_dir, save_file):
    import os
    texts = []
    for root, dirs, files in os.walk(shards_dir):
        for f in files:
            if not f.endswith('.tar'):
                print('invalid tar file', f)
                continue
            fp = os.path.join(root, f)
            tt = get_text(fp)
            texts.extend(tt)
    with open(save_file, 'w') as f:
        f.write(''.join(texts))
    print('done, get texts:', len(texts))


if __name__ == '__main__':
    from sys import argv
    shards_dir = argv[1]
    save_file = argv[2]
    main(shards_dir, save_file)
