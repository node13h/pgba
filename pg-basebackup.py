#!/bin/env python

# PostgreSQL backup automation and cleannup tool
# Copyright (C) 2016 Sergej Alikov <sergej@alikov.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import (
    print_function, unicode_literals, division, absolute_import)

import argparse
import sys
import os
from os.path import join, basename, isfile
import subprocess
from pwd import getpwnam
from grp import getgrnam
from datetime import datetime
import shutil
import logging

BACKUP_DIR = '/var/backup'
PGBASE_DEFAULT_DIR = join(BACKUP_DIR, 'pgbase')
PGARCHIVE_DEFAULT_DIR = join(BACKUP_DIR, 'pgarchive')
KEEP_DEFAULT = 5
USER_DEFAULT='postgres'


def run(args):
    process = subprocess.Popen(args)
    stdout, stderr = process.communicate()
    returncode = process.returncode

    if returncode != 0:
        raise RuntimeError('{} returned with non-zero exit code {}'.format(
            args[0], returncode))

    return returncode, stdout, stderr

def reverse_sorted_path_list(path, full=True):
    paths = reversed(sorted(os.listdir(path)))
    if full:
        return [join(path, e) for e in paths]
    else:
        return list(paths)

def backup_files_only(path_list):
    return [f for f in path_list if isfile(f) and f.endswith('.backup')]

def base_backups_only(path_list):
    return [p for p in path_list if isfile(join(p, 'backup_label'))]

def generated_backup_name():
    return datetime.now().strftime('%Y%m%d%H%M%S')

def last(l):
    try:
        element = l[-1]
    except IndexError:
        return None

    return element

def parse_args(argv):
    parser = argparse.ArgumentParser(
        description='Create and maintain PostgreSQL base backups')

    parser.add_argument('--pg-archivecleanup', required=True,
                        help='path to the pg_archivecleanup binary')
    parser.add_argument('--pgbase-path', default=PGBASE_DEFAULT_DIR,
                        help='target path to store the base backups')
    parser.add_argument('--pgarchive-path', default=PGARCHIVE_DEFAULT_DIR,
                        help='path to the WAL archive')
    parser.add_argument('--keep', type=int, default=KEEP_DEFAULT,
                        help='number of backups to keep')
    parser.add_argument('--user', default=USER_DEFAULT,
                        help='username to run backups as')
    parser.add_argument('--verbose', action='store_true', default=False,
                        help='enable verbose output')

    return parser.parse_args(argv)

def main(argv, logger):
    args = parse_args(argv)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    os.setgid(getgrnam(args.user).gr_gid)
    os.setuid(getpwnam(args.user).pw_uid)

    backup_name = generated_backup_name()
    backup_path = join(args.pgbase_path, backup_name)

    run(['pg_basebackup', '-D', backup_path, '-l', backup_name])

    base_backups_to_purge = base_backups_only(
        reverse_sorted_path_list(args.pgbase_path))[args.keep:]

    for backup_path in base_backups_to_purge:
        logger.info('Cleaning up {}'.format(backup_path))
        shutil.rmtree(backup_path)

    archives_to_purge = backup_files_only(
        reverse_sorted_path_list(args.pgarchive_path))[args.keep:]

    for archive in archives_to_purge:
        logger.info('Cleaning up {}'.format(archive))
        os.remove(archive)

    oldest_backup = last(backup_files_only(
        reverse_sorted_path_list(args.pgarchive_path)))

    if oldest_backup:
        logger.info('Running {} to clean the archives created before the {}'.format(
            args.pg_archivecleanup, oldest_backup))
        run([args.pg_archivecleanup, args.pgarchive_path, basename(oldest_backup)])

    return 0


if __name__ == '__main__':
    logging.basicConfig()
    logger = logging.getLogger(__name__)

    try:
        sys.exit(main(sys.argv[1:], logger))
    except Exception as e:
        logger.error('Unhandled exception occurred ({})'.format(str(e)))
