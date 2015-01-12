import time


def wait_until(predicate, interval):
    while not predicate():
        time.sleep(interval)


class Timer:
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.interval = self.end - self.start
