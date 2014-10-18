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
from serial.serialutil import SerialException

from . import log, __version__, __git__
from rx import RxThread
from protocol import Protocol

logger = log.fuct_logger('fuctlog')


###
### Trigger
###


def trigger():
    parser = argparse.ArgumentParser(
        prog='fucttrigger',
        description='''FUCT - FreeEMS Unified Console Tools, version: %s

  'fucttrigger' is a tool to adjust the decoder trigger angle on a fresh FreeEMS install. You need a timinglight
  or a similar tool to check the correct alignment. Also make sure you use flat timing tables (ex. 10 deg) so you get
  a good consistent reading. An initial angle can be used to load it to the device when the application is started.

  Example: fucttrigger -a 180 /dev/ttyUSB0''' % __version__,
        formatter_class=argparse.RawTextHelpFormatter,)
    parser.add_argument('-v', '--version', action='store_true', help='show program version')
    parser.add_argument('-d', '--debug', action='store_true', help='show debug information')
    parser.add_argument('-a', '--angle', type=int, nargs='?', help='initial trigger angle')
    parser.add_argument('serial', nargs='?', help='serialport device (eg. /dev/xxx, COM1)')

    args = parser.parse_args()

    if args.version:
        print "fucttrigger %s (Git: %s)" % (__version__, __git__)
    elif args.serial is not None:
        try:
            if args.debug:
                logger.setLevel(logging.DEBUG)

            logger.info("Opening port %s" % args.serial)
            ser = serial.Serial(args.serial, 115200, timeout=0.02, bytesize=8, parity='O', stopbits=1)
            logger.debug(ser)

            queue_in = Queue.Queue(0)
            queue_out = Queue.Queue(0)

            p = RxThread(ser, queue_in)
            p.start()

            init = True
            angle_value = 0
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
                            angle_value = struct.unpack('>H', data[1])[0] / 50
                            logger.info("Current trigger angle: %d deg" % angle_value)
                            if args.angle is not None:
                                angle_value = args.angle
                                logger.info("Initial trigger angle: %d deg" % angle_value)
                                angle = struct.pack('>H', (args.angle * 50))
                                queue_out.put(Protocol.create_packet(Protocol.FE_CMD_FLASH_WRITE, location=Protocol.FE_LOCATION_TRIGGER, data=angle, use_length=True))
                            logger.info("Commands: a = +1, z = -1, s = +10, x = -10)")
                            init = False
                    else:
                        if data[0] == Protocol.FE_CMD_FLASH_WRITE + 1:
                            logger.info("Trigger angle: %d deg" % angle_value)

                except Queue.Empty:
                    pass

                if not init:
                    line = raw_input('>>> ')
                    angle_new = angle_value
                    if line == 'a':
                        angle_new += 1
                    elif line == 'z':
                        angle_new -= 1
                    elif line == 's':
                        angle_new += 10
                    elif line == 'x':
                        angle_new -= 10

                    if angle_new != angle_value:
                        angle_value = angle_new
                        angle = struct.pack('>H', (angle_value * 50))
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


