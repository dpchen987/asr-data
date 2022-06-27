import sys
import os
import time


class MyProcessBar:
    def __init__(self, total, symbol='='):
        ts = os.get_terminal_size()
        width = ts.columns // 2
        self.total = total
        self.width = width
        self.symbol = symbol
        self.last_time = time.time()
        self.last_i = 0
        self.max_len = 0

    def show(self, i, prefix=''):
        now = time.time()
        speed = round((i - self.last_i) / (now - self.last_time), 2)
        self.last_i = i
        self.last_time = now
        percent = i / self.total
        size = int(self.width * percent)
        passed = self.symbol * size
        left = ' ' * (self.width - size)
        percent = int(percent*100)
        bar = (
                f'\r{prefix} [{passed}{left}] {i}/{self.total} '
                f'({percent: 3}%) {speed}/s'
                )
        if len(bar) < self.max_len:
            bar += ' ' * (self.max_len - len(bar))
        else:
            self.max_len = len(bar)
        # print(bar, file=sys.stdout, end='')
        sys.stdout.write(bar)
        sys.stdout.flush()

    def done(self):
        print('')


if __name__ == '__main__':
    import time
    p = MyProcessBar(10)
    for i in range(10):
        p.show(i+1)
        time.sleep(0.5)
    p.done()
