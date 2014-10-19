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

  'fucttrigger' is a tool to adjust the decoder trigger angle on a fresh FreeEMS install. You need a timinglight
  or a similar tool to check the correct alignment. Also make sure you use flat timing tables (ex. 10 deg) so you get
  a good consistent reading. An initial angle can be used to load it to the device when the application is started.

  Example: fucttrigger -a 180 /dev/ttyUSB0''' % (__version__, __git__),
        formatter_class=argparse.RawTextHelpFormatter,)
    parser.add_argument('-v', '--version', action='store_true', help='show program version')
    parser.add_argument('-d', '--debug', action='store_true', help='show debug information')
    parser.add_argument('-a', '--angle', type=check_angle_arg, nargs='?', help='initial trigger angle in degrees (0-719.98)')
    parser.add_argument('serial', nargs='?', help='serialport device (eg. /dev/xxx, COM1)')

    args = parser.parse_args()

    if args.version:
        print "fucttrigger %s (Git: %s)" % (__version__, __git__)
    elif args.serial is not None:
        try:
            if args.debug:
                logger.setLevel(logging.DEBUG)

            logger.info("Opening port %s" % args.serial)
            ser = serial.Serial(args.serial, 115200, timeout=0.02, bytesize=8, parity=serial.PARITY_ODD, stopbits=1)
            logger.debug(ser)

            queue_in = Queue.Queue(0)
            queue_out = Queue.Queue(0)

            p = RxThread(ser, queue_in)
            p.start()

            init = True
            angle_value = 0  # 1 unit = 0.02 deg
            queue_out.put(Protocol.create_packet(Protocol.FE_CMD_DECODER))

            while True:
                try:
                    time.sleep(0.2)
                    packet = queue_out.get(False)
                    ser.write(packet)
                    ser.flush()
                except Queue.Empty:
                    pass

                try:
                    msg = queue_in.get(False)
                    data = Protocol.decode_packet(msg)

                    if init:
                        if data[0] == Protocol.FE_CMD_DECODER + 1:
                            logger.info("Decoder: %s" % data[1])
                            queue_out.put(Protocol.create_packet(Protocol.FE_CMD_FLASH_READ, location=Protocol.FE_LOCATION_TRIGGER, size=2))
                        if data[0] == Protocol.FE_CMD_FLASH_READ + 1:
                            angle_value = struct.unpack('>H', data[1])[0]
                            logger.info("Current trigger angle: %.2f deg" % to_angle(angle_value))
                            if args.angle is not None:
                                angle_value = to_raw_angle(args.angle)
                                logger.info("Initial trigger angle: %.2f deg" % args.angle)
                                angle = struct.pack('>H', angle_value)
                                queue_out.put(Protocol.create_packet(Protocol.FE_CMD_FLASH_WRITE, location=Protocol.FE_LOCATION_TRIGGER, data=angle, use_length=True))
                            logger.info("Type a new value (0-%d) or use predefined commands" % ANGLE_MAX)
                            logger.info("Commands: a = +1, z = -1, s = +10, x = -10, d = +0.1, c = -0.1)")
                            init = False
                    else:
                        if data[0] == Protocol.FE_CMD_FLASH_WRITE + 1:
                            logger.info("Trigger angle: %.2f deg" % to_angle(angle_value))

                except Queue.Empty:
                    pass

                if not init:
                    line = raw_input('>>> ')
                    angle_new = angle_value
                    if line == 'a':
                        angle_new += ANGLE_FACTOR
                    elif line == 'z':
                        angle_new -= ANGLE_FACTOR
                    elif line == 's':
                        angle_new += ANGLE_FACTOR * 10
                    elif line == 'x':
                        angle_new -= ANGLE_FACTOR * 10
                    elif line == 'd':
                        angle_new += ANGLE_FACTOR / 10
                    elif line == 'c':
                        angle_new -= ANGLE_FACTOR / 10
                    elif re.match("^(?=.*\d)\d{1,3}(?:\.\d{1,2})?$", line) is not None:
                        v = float(line)
                        if v >= 0 or v <= ANGLE_MAX:
                            angle_new = to_raw_angle(v)
                        else:
                            logger.error("Invalid angle value, use 0-%d" % ANGLE_MAX)

                    if angle_new != angle_value:
                        angle_value = angle_new
                        angle = struct.pack('>H', angle_value)
                        logger.info("Setting value to %d" % angle_new)
                        queue_out.put(Protocol.create_packet(Protocol.FE_CMD_FLASH_WRITE, location=Protocol.FE_LOCATION_TRIGGER, data=angle, use_length=True))

        except KeyboardInterrupt:
            logger.info("logging stopped")
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


def to_angle(value):
    return float(value) / ANGLE_FACTOR


def to_raw_angle(value):
    return round(float(value) * ANGLE_FACTOR)


def check_angle_arg(value):
    v = float(value)
    if v < 0 or v > ANGLE_MAX:
        raise argparse.ArgumentTypeError("Value %s is invalid, use 0-%d." % (v, ANGLE_MAX))
    return v
