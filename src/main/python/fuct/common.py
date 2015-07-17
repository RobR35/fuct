# -*- coding: utf-8 -*-
#
# This file is part of fuct. Copyright (c) 2014 Ari Karhu.
# See the LICENSE file for license rights and limitations (MIT).
#

__author__ = 'ari'

import sys


def print_progress(progress, bar_length=20):
    hashes = '#' * int(round(progress * bar_length))
    spaces = ' ' * (bar_length - len(hashes))
    sys.stdout.write("\rProgress: [{0}] {1}%".format(hashes + spaces, int(round(progress * 100))))
    sys.stdout.flush()
