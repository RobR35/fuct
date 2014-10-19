# -*- coding: utf-8 -*-
#
# This file is part of fuct. Copyright (c) 2014 Ari Karhu.
# See the LICENSE file for license rights and limitations (MIT).
#

__author__ = 'ari'

import logging
import argparse
import serial
import Queue
import time
import struct
import re
from serial.serialutil import SerialException

from . import log, __version__, __git__
from rx import RxThread
from protocol import Protocol
import binascii
import sys

logger = log.fuct_logger('fuctlog')


###
### Trigger
###

ANGLE_FACTOR = 50.00
ANGLE_MAX = 719.98


def trigger():
    parser = argparse.ArgumentParser(
        prog='fucttrigger',
        description='''FUCT - FreeEMS Unified Console Tools, version: %s (Git: %s)

  'fucttrigger' is a tool to adjust the decoder trigger offset on a fresh FreeEMS install. You need a timinglight
  or a similar tool to check the correct alignment. Also make sure you use flat timing tables (ex. 10 deg BTDC) so
  you get a good consistent reading. An initial offset can be used to load it to the device when the application
  is started.

  Example: fucttrigger -o 90 /dev/ttyUSB0''' % (__version__, __git__),
        formatter_class=argparse.RawTextHelpFormatter,)
    parser.add_argument('-v', '--version', action='store_true', help='show program version')
    parser.add_argument('-d', '--debug', action='store_true', help='show debug information')
    parser.add_argument('-o', '--offset', type=check_offset_arg, nargs='?', help='initial trigger offset in degrees ATDC (0-719.98)')
    parser.add_argument('serial', nargs='?', help='serialport device (eg. /dev/xxx, COM1)')

    args = parser.parse_args()

    if args.version:
        print "fucttrigger %s (Git: %s)" % (__version__, __git__)
    elif args.serial is not None:
        logger.info("FUCT - fucttrigger %s (Git: %s)" % (__version__, __git__))
        try:
            if args.debug:
                logger.setLevel(logging.DEBUG)

            logger.info("Opening port %s" % args.serial)
            ser = serial.Serial(args.serial, 115200, timeout=0.02, bytesize=8, parity=serial.PARITY_ODD, stopbits=1)
            logger.debug(ser)

            queue_in = Queue.Queue(0)
            queue_out = Queue.Queue(0)

            rx = RxThread(ser, queue_in)
            rx.start()

            init = True
            offset_value = 0  # 1 unit = 0.02 deg
            queue_out.put(Protocol.create_packet(Protocol.FE_CMD_DECODER))

            while True:
                try:
                    time.sleep(0.2)
                    packet = queue_out.get(False)
                    if logger.getEffectiveLevel() == logging.DEBUG:
                        logger.debug("--> %s" % binascii.hexlify(packet[1:-2]))
                    ser.write(packet)
                    ser.flush()
                except Queue.Empty:
                    pass

                try:
                    msg = queue_in.get(False)
                    if logger.getEffectiveLevel() == logging.DEBUG:
                        logger.debug("<-- %s" % binascii.hexlify(msg))
                    data = Protocol.decode_packet(msg)

                    if init:
                        if data[0] == Protocol.FE_CMD_DECODER + 1:
                            logger.info("Decoder: %s" % data[1])
                            queue_out.put(read_trigger_message(flash=True))
                        if data[0] == Protocol.FE_CMD_FLASH_READ + 1:
                            offset_value = struct.unpack('>H', data[1])[0]
                            logger.info("Current trigger offset in flash: %.2f deg" % to_angle(offset_value))
                            if args.offset is not None:
                                offset_value = to_raw_angle(args.offset)
                                logger.info("Initial trigger offset: %.2f deg" % args.offset)
                                queue_out.put(write_trigger_message(struct.pack('>H', offset_value), flash=True))
                            logger.info("Type a new value (0-%.2f) or use predefined commands" % ANGLE_MAX)
                            logger.info("Commands: 'a' => +1, 'z' => -1, 's' => +10, 'x' => -10, 'd' => +0.1, 'c' => -0.1")
                            logger.info("          'quit' or 'exit' => Exit program")
                            init = False
                    else:
                        if data[0] == Protocol.FE_CMD_FLASH_WRITE + 1:
                            logger.info("Trigger offset: %.2f deg" % to_angle(offset_value))

                except Queue.Empty:
                    pass

                if not init:
                    line = raw_input('>>> ')
                    offset_new = offset_value
                    if line == 'a':
                        offset_new += ANGLE_FACTOR
                    elif line == 'z':
                        offset_new -= ANGLE_FACTOR
                    elif line == 's':
                        offset_new += ANGLE_FACTOR * 10
                    elif line == 'x':
                        offset_new -= ANGLE_FACTOR * 10
                    elif line == 'd':
                        offset_new += ANGLE_FACTOR / 10
                    elif line == 'c':
                        offset_new -= ANGLE_FACTOR / 10
                    elif re.match("^(?=.*\d)\d{1,3}(?:\.\d{1,2})?$", line) is not None:
                        v = float(line)
                        if v >= 0 or v <= ANGLE_MAX:
                            offset_new = to_raw_angle(v)
                        else:
                            logger.error("Invalid value, use 0-%.2f" % ANGLE_MAX)
                    elif line == 'exit' or line == 'quit':
                        rx.stop()
                        logger.info("Exiting...")
                        sys.exit(0)

                    if offset_new != offset_value:
                        offset_value = offset_new
                        if logger.getEffectiveLevel() == logging.DEBUG:
                            logger.debug("Raw offset value: %d" % offset_new)
                        queue_out.put(write_trigger_message(struct.pack('>H', offset_value), flash=True))

        except KeyboardInterrupt:
            rx.stop()
            logger.info("Exiting...")
        except NotImplementedError, ex:
            logger.error(ex.message)
        except (AttributeError, ValueError), ex:
            logger.error(ex.message)
        except SerialException, ex:
            logger.error("Serial: " + ex.message)
        except OSError, ex:
            logger.error("OS: " + ex.strerror)
    else:
        parser.print_usage()


def write_trigger_message(offset, flash=False):
    return Protocol.create_packet(
        Protocol.FE_CMD_RAM_WRITE if flash is False else Protocol.FE_CMD_FLASH_WRITE,
        location=Protocol.FE_LOCATION_TRIGGER,
        data=offset,
        use_length=True)


def read_trigger_message(flash=False):
    return Protocol.create_packet(
        Protocol.FE_CMD_RAM_READ if flash is False else Protocol.FE_CMD_FLASH_READ,
        location=Protocol.FE_LOCATION_TRIGGER,
        size=2)


def to_angle(value):
    return float(value) / ANGLE_FACTOR


def to_raw_angle(value):
    return round(float(value) * ANGLE_FACTOR)


def check_offset_arg(value):
    v = float(value)
    if v < 0 or v > ANGLE_MAX:
        raise argparse.ArgumentTypeError("Value %s is invalid, use 0-%.2f." % (v, ANGLE_MAX))
    return v
