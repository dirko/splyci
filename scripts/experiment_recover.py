# Experiments related to recovering the original sheets

import os
import glob
import sys
import time
from splyci.integration import extract


def main(indir, outdir):
    for dataset in ['develop', 'test']:
        files = glob.glob(indir + f'/{dataset}/*.xlsx')
        for file in files:
            base_name = file.split('.')[0].split('/')[-1]
            file_dir = outdir + '/' + dataset + '/' + base_name
            os.makedirs(file_dir, exist_ok=True)
            sheets_in = [(file, 1), (file, 2)]
            extract(sheets_in, file_dir)


if __name__ == '__main__':
    command = sys.argv[1]
    indir = sys.argv[2]
    outdir = sys.argv[3]
    if command == 'merge':
        main(indir=indir, outdir=outdir)
