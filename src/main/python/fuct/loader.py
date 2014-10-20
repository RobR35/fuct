# -*- coding: utf-8 -*-
#
# This file is part of fuct. Copyright (c) 2014 Ari Karhu.
# See the LICENSE file for license rights and limitations (MIT).
#

__author__ = 'ari'

import logging
import os
import argparse
import serial
import textwrap
from serial.serialutil import SerialException

from . import validator, device, log, pages, __version__, __git__

logger = log.fuct_logger('fuctlog')


class CmdHandler:

    def __init__(self):
        pass

    def lookup_method(self, command):
        method = getattr(self, 'do_%s' % command.lower(), None)
        if callable(method):
            return method
        else:
            raise NotImplementedError('Command "%s" not implemented' % command)

    @staticmethod
    def is_ascii(s):
        return all(c < 128 for c in s)

    @staticmethod
    def get_device(port):
        dev = device.Device(port)
        dev.reinit()
        if dev.check_device:
            return dev

        raise ValueError('Device problem')

    @staticmethod
    def do_check(params):
        if params[1] is not None:
            if os.path.isfile(params[1]) and os.access(params[1], os.R_OK):
                logger.info("Checking firmware...")
                records = validator.verify_firmware(params[1])
                if records:
                    logger.info("Parsed %d records" % len(records))
                    if records[0].stype[0] == 'S0':
                        header = records[0].data if CmdHandler.is_ascii(records[0].data) else "[binary data]"
                        logger.info("Header info: [%s]" % header)
                    else:
                        logger.warning("No header...")
                    logger.info("File OK")
                    return True
                else:
                    return False
            else:
                raise ValueError('Cannot find firmware file or no read access')

        raise ValueError('No firmware given')

    @staticmethod
    def do_device(params):
        if params[0] is not None:
            logger.info("Checking device...")
            dev = CmdHandler.get_device(params[0])
            dev.analyse_device()

            return True

        raise ValueError('serial port argument cannot be empty')

    @staticmethod
    def do_load(params, verify=True):
        if params[0] is not None and params[1] is not None:
            logger.info("Checking firmware file...")
            records = validator.verify_firmware(params[1])
            if records is None:
                raise ValueError('Firmware file is corrupt or has no records, won\'t load')
            logger.info("File OK, got %d records" % len(records))

            dev = CmdHandler.get_device(params[0])

            logger.info("Converting records to memory pages...")
            header = records.pop(0)  # S0 Record
            termination = records.pop()  # S8 Record
            pagelist = pages.records_to_pages(records)
            logger.info("Received %d pages" % len(pagelist))
            logger.info("Loading firmware: '%s'" % str(header.data))

            last_page = None
            for page in pagelist:
                logger.info("%6d bytes to 0x%02x @ 0x%04x" % (len(page.data), page.page, page.address))
                dev.erase_and_write(page, erase=False if page.page == last_page else True, verify=verify)
                last_page = page.page

            return True

        raise ValueError("Can't load sh*t captain, no file nor serial?!")

    @staticmethod
    def do_fastload(params):
        CmdHandler.do_load(params, False)

    @staticmethod
    def do_rip(params):
        if params[0] is not None:
            dev = CmdHandler.get_device(params[0])
            logger.info("Ripping pages from 0xE0 to 0xFF")
            dev.rip_and_save_pages('demo.s19', 0xE0, 0xFF)

            return True

        raise ValueError('serial port argument cannot be empty')

    @staticmethod
    def do_erase(params):
        if params[0] is not None:
            dev = CmdHandler.get_device(params[0])
            logger.info("Erasing pages from 0xE0 to 0xFF")
            resp = dev.erase_pages(0xE0, 0xFF)  # TODO: get pages from device info

            return True

        raise ValueError('serial port argument cannot be empty')

###
### Loader
###


def loader():
    parser = argparse.ArgumentParser(
        prog='fuctloader',
        description='''FUCT - FreeEMS Unified Console Tools, version: %s (Git: %s)

  'fuctloader' is a firmware loader application for FreeEMS. With this tool you can check your device info,
  validate S19 files and of course load, verify, rip and erase firmware data. You can also rip the serial
  monitor for further analysis.

  Example: fuctloader -s /dev/ttyUSB0 load testcar1-firmware.S19''' % (__version__, __git__),
        formatter_class=argparse.RawTextHelpFormatter,)
    parser.add_argument('-v', '--version', action='store_true', help='show program version')
    parser.add_argument('-d', '--debug', action='store_true', help='show debug information')
    parser.add_argument('-s', '--serial', nargs='?', help='serialport device (eg. /dev/xxx, COM1)')
    parser.add_argument(
        'command',
        nargs='?',
        help=textwrap.dedent('''\
        command to execute. available commands:

        check      validate S19 firmware file (no device needed)
        device     poll device for correct device ID and serial monitor
        load       validate, load and verify firmware file into device
        fastload   load firmware file into device without any validation
        rip        rip firmware from device
        erase      erase device (serial monitor is not erased)

        '''))
    parser.add_argument('firmware', nargs='?', help='location and name of the S19 firmware file')

    args = parser.parse_args()

    if args.version:
        print "fuctloader %s (Git: %s)" % (__version__, __git__)
    elif args.command is not None:
        logger.info("FUCT - fuctloader %s (Git: %s)" % (__version__, __git__))
        try:
            ser = None
            if args.debug:
                logger.setLevel(logging.DEBUG)
            if args.serial is not None:
                logger.info("Opening port %s" % args.serial)
                ser = serial.Serial(args.serial, 115200, timeout=0.02, bytesize=8, parity=serial.PARITY_NONE, stopbits=1)
                logger.debug(ser)
            if CmdHandler().lookup_method(args.command)((ser, args.firmware)):
                logger.info("Exiting...")
            else:
                logger.error("Exiting on error")
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
