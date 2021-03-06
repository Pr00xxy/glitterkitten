#!/usr/bin/env python3

import argparse
import os
import sys
import threading
import time
from pathlib import Path

from webptools import webplib as webp

parser = argparse.ArgumentParser(description='description')

required = parser.add_argument_group('required arguments')
optional = parser.add_argument_group('optional arguments')

required.add_argument('--config', dest='config', action='store', default=None, required=True, help='cwebp arguments')
required.add_argument('--source_dir', dest='source_dir', action='store', default=None, required=True, help='Source root for files')
required.add_argument('--result_dir', dest='result_dir', action='store', default=None, help='Target location for encoded file, leave empty for same as source')

optional.add_argument('--threads', dest='threads', action='store', default=1, help='Amount of concurrent threads')
optional.add_argument('--types', dest='types', action='store', default='jpg,png', help='File types to encode. default: jpg,png')
optional.add_argument('--matches', dest='matches', action='store', default=[], help='Glob match files, matches all by default')

optional.add_argument('-d', dest='purge', action='store_true', default=False, help='Delete existing webp file')
optional.add_argument('-check_size', dest='check_size', action='store_true', default=False, help='E')

args = parser.parse_args()


class Glitterkitten(object):
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

        file_collection = self.get_all_input_files(self.types)

        if len(file_collection) is 0:
            print('Could not find any files')
            return

        self.file_no = len(file_collection)

        print('Files:   {0}'.format(self.file_no))
        print('Threads: {0} \n'.format(self.threads))

        time.sleep(1)
        start = time.time()

        try:

            chunks = list(chunk(file_collection, self.threads))
            thread_pool = self.create_thread_pool(chunks, self.threads)

            for thread in thread_pool:
                thread.start()

            while self.progress < self.file_no:
                time.sleep(1)
                if self.progress == self.file_no:
                    break

        except (KeyboardInterrupt, SystemExit):
            self.kill_workers()
            print('Premature exit by user')
            sys.exit(1)

        stop = time.time()

        print('Images processed: {0} \nTime: {1}s'.format(self.file_no, format(stop - start, '.4f')))

    def kill_workers(self):
        self.thread_kill = True

    def should_die(self):
        return self.thread_kill

    def create_thread_pool(self, splits, thread_count: int):
        threads = []
        for i in range(thread_count):
            t = threading.Thread(target=self.transcode_file, args=(i, splits[i],))
            threads.append(t)
        return threads

    def transcode_file(self, worker_id, files):
        processed = 0

        for file in files:

            if self.should_die():
                sys.exit(1)

            original_file = str(file)

            webp_file = self.get_new_file_path('{0}.webp'.format(original_file))

            self.progress += 1
            processed += 1
            result = '✓'

            if self.purge:
                if file_exists(webp_file):
                    print('({0}/{1}) Deleting existing {2} {3}'.format(self.progress, self.file_no, '?', webp_file))
                    remove_file(webp_file)

            if not file_exists(webp_file):
                try:
                    create_file_path(webp_file)
                    webp.cwebp(original_file, webp_file, self.config)
                except Exception as e:
                    print('Failed transcoding file: {0} {1}'.format(webp_file, repr(e)))
                    continue

            if self.check_size:
                if os.path.getsize(webp_file) > os.path.getsize(original_file):
                    remove_file(webp_file)
                    result = '×'

            print('({0}/{1}) {2} {3}'.format(self.progress, self.file_no, result, webp_file))

        print('Thread {0} Completed. Processed {1}/{2}'.format(worker_id, processed, len(files)))

        return True

    def get_all_input_files(self, types: str):
        file_types = types.split(',')
        result_array = []
        for file_type in file_types:
            for file in Path(self.source_dir).glob('**/*.' + file_type):
                result_array.append(file)

        return result_array

    def get_new_file_path(self, file: str):
        new_path = file
        new_path = new_path.replace(self.source_dir, self.result_dir)
        return new_path


def file_exists(file: str):
    return os.path.exists(file)


def remove_file(file: str):
    return os.remove(file)


def create_file_path(file: str):
    if not os.path.exists(os.path.dirname(file)):
        return os.makedirs(os.path.dirname(file))


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
