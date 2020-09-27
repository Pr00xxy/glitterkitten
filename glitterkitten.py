#!/usr/bin/env python3

from webptools import webplib as webp
from pathlib import Path
import threading
import argparse
import time
import sys
import os
import re

parser = argparse.ArgumentParser(description='description')

required = parser.add_argument_group('required arguments')
optional = parser.add_argument_group('optional arguments')

required.add_argument('--config', dest='config', action='store', default=None, required=True, help='cwebp arguments')
required.add_argument('--source_dir', dest='source_dir', action='store', default=None, required=True,
                      help='Source root for files')

optional.add_argument('--threads', dest='threads', action='store', default=1, help='Amount of concurrent threads')
optional.add_argument('--types', dest='types', action='store', default='jpg,png',
                      help='File types to encode. default: jpg,png')
optional.add_argument('--matches', dest='matches', action='store', default=[],
                      help='Glob match files, matches all by default')
optional.add_argument('--result_dir', dest='result_dir', action='store', default=None,
                      help='Target location for encoded file, leave empty for same as source')

optional.add_argument('-d', dest='purge', action='store_true', default=False, help='Override existing webp files')
optional.add_argument('-check_size', dest='check_size', action='store_true', default=False,
                      help='Revert encoding if resulting webp > source')

args = parser.parse_args()


class Glitterkitten(object):
    file_array = None
    file_no = None
    progress = 0
    thread_kill = False

    def __init__(
            self,
            config,
            source_dir,
            threads,
            check_size,
            types,
            result_dir,
            purge,
            matches
    ):
        self.config = config
        self.source_dir = source_dir
        self.threads = threads
        self.check_size = check_size
        self.types = types
        self.result_dir = result_dir
        self.purge = purge
        self.matches = matches

    def run(self):
        raw_file_collection = self.get_all_input_files()

        if len(raw_file_collection) is 0:
            print('Could not find any files')
            return

        self.file_array = raw_file_collection
        self.file_no = len(raw_file_collection)

        print('Files:   {0}'.format(self.file_no))
        print('Threads: {0} \n'.format(self.threads))

        time.sleep(1)
        start = time.time()

        try:
            splits = list(chunk(self.file_array, self.threads))
            thread_pool = self.create_thread_pool(splits)

            for thread in thread_pool:
                thread.start()

            while self.progress < self.file_no:
                time.sleep(1)
                if self.progress == self.file_no:
                    break

        except (KeyboardInterrupt, SystemExit):
            self.thread_kill = True
            sys.exit(1)

        stop = time.time()

        print('Images processed: {0} \nTime: {1}s'.format(self.file_no, format(stop - start, '.4f')))

    def create_thread_pool(self, splits):
        threads = []
        for i in range(self.threads):
            t = threading.Thread(target=self.transcode_file, args=(i, splits[i],))
            threads.append(t)
        return threads

    def transcode_file(self, worker_id, files):
        processed = 0

        for file in files:
            try:
                self.progress += 1
                processed += 1
                result = '✓'

                if self.thread_kill is True:
                    sys.exit(1)

                webp_file = '{0}.webp'.format(str(file))
                orginal_file = str(file)

                if self.purge:
                    if file_exists(webp_file):
                        print('({0}/{1}) Deleting existing {2} {3}'.format(self.progress, self.file_no, '?', webp_file))
                        remove_file(webp_file)

                if not file_exists(webp_file):
                    webp.cwebp(str(file), webp_file, self.config)

                if self.check_size:
                    if os.path.getsize(webp_file) > os.path.getsize(orginal_file):
                        remove_file(webp_file)
                        result = '×'

                print('({0}/{1}) {2} {3}'.format(self.progress, self.file_no, result, webp_file))

            except Exception as e:
                print('Failed transcoding file: {0} {1}'.format(file, repr(e)))

        print('Thread {0} Completed. Processed {1}/{2}'.format(worker_id, processed, len(files)))

        return True

    def get_all_input_files(self):
        file_types = self.get_all_file_types()
        result_array = []
        for file_type in file_types:
            for file in Path(self.source_dir).glob('**/*.' + file_type):
                result_array.append(file)

        return result_array

    def get_all_file_types(self):
        return self.types.split(',')


def file_exists(file: str):
    return os.path.exists(file)


def remove_file(file: str):
    return os.remove(file)


def chunk(seq, num):
    avg = len(seq) / float(num)
    out = []
    last = 0.0

    while last < len(seq):
        # TODO: what the fuck does this do?
        out.append(seq[int(last):int(last + avg)])
        last += avg

    return out


glitterkitten = Glitterkitten(
    config=args.config,
    source_dir=args.source_dir,
    threads=int(args.threads),
    check_size=args.check_size,
    types=args.types,
    result_dir=args.result_dir,
    purge=args.purge,
    matches=args.matches
)

glitterkitten.run()
