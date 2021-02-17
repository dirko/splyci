import sys
import time
from splyci.integration import extract


if __name__ == '__main__':
    fileout = sys.argv[1]
    files = [(fn.split(':')[0], int(fn.split(':')[1])) for fn in sys.argv[2:]]
    start = time.time()
    print('start time:', start)
    extract(files, fileout)
    end = time.time()
    print('end time:', end)
    print('timediff: ', end - start)
