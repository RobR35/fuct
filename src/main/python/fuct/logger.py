# -*- coding: utf-8 -*-
#
# This file is part of fuct. Copyright (c) 2014 Ari Karhu.
# See the LICENSE file for license rights and limitations (MIT).
#

__author__ = 'ari'

import sys
import logging
import argparse
import serial
import time
import math
import os.path
from serial.serialutil import SerialException

from . import log, __version__, __git__

LOG = log.fuct_logger('fuctlog')


###
### Logger
###


def logger():
    parser = argparse.ArgumentParser(
        prog='fuctlogger',
        description='FUCT - FreeEMS Unified Console Tool, version: %s' % __version__,
        formatter_class=argparse.RawTextHelpFormatter,)
    parser.add_argument('-v', '--version', action='store_true', help='show program version')
    parser.add_argument('-d', '--debug', action='store_true', help='show debug information')
    parser.add_argument('-p', '--path', nargs='?', help='path for the logfile (default ./)')
    parser.add_argument('-x', '--prefix', nargs='?', help='prefix for the logfile name')
    parser.add_argument('-s', '--size', nargs='?', help='size of single logfile with unit (xxM/xxG) (default 128M)')
    parser.add_argument('serial', nargs='?', help='serialport device (eg. /dev/xxx, COM1)')

    args = parser.parse_args()

    if args.version:
        print "fuctlogger %s (Git: %s)" % (__version__, __git__)
    elif args.serial is not None:
        try:
            if args.debug:
                LOG.setLevel(logging.DEBUG)

            LOG.info("Opening port %s" % args.serial)
            ser = serial.Serial(args.serial, 115200, timeout=0.02, bytesize=8, parity='N', stopbits=1)
            LOG.debug(ser)

            basename = logname = create_filename(args.prefix, args.path)
            LOG.info("Opening logfile: %s" % logname)
            logfile = open(logname, 'w')

            sizelimit = convert_sizelimit(args.size) if args.size is not None else 128000000
            LOG.info("Setting logfile size to: %d bytes" % sizelimit)

            LOG.info("Start logging... (Ctrl+C to quit)")
            spinner = busy_icon()
            logcounter = 1
            while True:
                buf = ser.read(1024)

                if os.path.getsize(logname) >= sizelimit:
                    logfile.close()
                    logname = "%s.%d" % (basename, logcounter)
                    logfile = open(logname, 'w')
                    sys.stdout.flush()
                    sys.stdout.write('\b')
                    LOG.info("=> %s" % logname)
                    logcounter += 1

                logfile.write(buf)

                sys.stdout.write(spinner.next())
                sys.stdout.flush()
                sys.stdout.write('\b')
        except KeyboardInterrupt:
            LOG.info("Logging stopped")
            ser.close()
            logfile.close()
        except NotImplementedError, ex:
            LOG.error(ex.message)
        except (AttributeError, ValueError), ex:
            LOG.error(ex.message)
        except SerialException, ex:
            LOG.error("Serial: " + ex.message)
        except OSError, ex:
            LOG.error("OS: " + ex.strerror)
    else:
        parser.print_usage()


def create_filename(prefix, path):
    logname = "%s-%s.bin" % (prefix if prefix is not None else "log", time.strftime("%Y%m%d-%H%M%S"))
    if path is not None:
        logname = os.path.join(path, logname)
    return logname


def convert_sizelimit(limit):
    unit = limit[-1]
    size = limit[:-1]
    if size.isdigit():
        if unit == 'M':
            return int(size) * math.pow(1000, 2)
        if unit == 'G':
            return int(size) * math.pow(1000, 3)
        else:
            raise ValueError("Size has invalid unit (%s)" % unit)
    else:
        raise ValueError("Size (%s) is not numeric value" % size)


def busy_icon():
    while True:
        for cursor in '|/-\\':
            yield cursor