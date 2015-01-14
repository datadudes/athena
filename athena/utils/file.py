import csv
import time
from os import makedirs
import errno
from os.path import join as path_join


def write_csv(csv_file, rows, headers=None):
    with open(csv_file, 'wb') as f:
        csv_writer = csv.writer(f)
        if headers:
            csv_writer.writerow(headers)
        csv_writer.writerows(rows)


def mkdir_p(path):
    """Emulates `mkdir -p` behavior."""
    try:
        makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise


def touchopen(filename, mode='r'):
    """Opens a file in the requested mode. Creates the file if it doesn't exist"""
    try:
        f = open(filename, mode)
    except IOError as exc:
        if exc.errno == errno.ENOENT:
            open(filename, 'a').close()
            f = open(filename, mode)
        else:
            raise
    return f


def create_tmp_dir(prefix=''):
    dirpath = path_join('/tmp', prefix + str(int(time.time() * 1000)))
    mkdir_p(dirpath)
    return dirpath
