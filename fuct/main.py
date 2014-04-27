
import logging
import os
import argparse
import serial

from . import validator
from . import device
from . import log
from . import pages
from . import __version__


class CmdHandler:

    def __init__(self):
        pass

    def lookup_method(self, command):
        return getattr(self, 'do_' + command.lower(), None)

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
    def do_load(params):
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
                logger.info("%d bytes to %02x @ %04x" % (len(page.data), page.page, page.address))
                dev.erase_and_write(page, erase=False if page.page == last_page else True)
                last_page = page.page

            return True

        raise ValueError('cannot load shit captain, no file nor serial?!')

    @staticmethod
    def do_fastload(params):
        if params[0] is not None and params[1] is not None:
            return "fastloaded..." + params[0]

        raise ValueError('firmware and serial port arguments cannot be empty')

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

    @staticmethod
    def do_unknown(self, rest):
        raise NotImplementedError('received unknown command')


### Main


def main():
    parser = argparse.ArgumentParser(description='FUCT - FreeEMS Unified Console Tool, version: %s' % __version__)
    parser.add_argument('-v', '--version', action='store_true', help='show program version')
    parser.add_argument('-d', '--debug', action='store_true', help='show debug information')
    parser.add_argument('-s', '--serial', nargs='?', help='serialport device (eg. /dev/xxx, COM1)')
    parser.add_argument('command', nargs='?', help='device, check, load, fastload, rip, erase')
    parser.add_argument('firmware', nargs='?', help='location of the S19 firmware file')

    args = parser.parse_args()

    if args.version:
        print "fuct %s" % __version__
    elif args.command is not None:
        try:
            ser = None
            if args.debug:
                logger.setLevel(logging.DEBUG)
            if args.serial is not None:
                logger.info("Opening port %s" % args.serial)
                ser = serial.Serial(args.serial, 115200, timeout=0.1, bytesize=8, parity='N', stopbits=1)
                logger.debug(ser)
            if CmdHandler().lookup_method(args.command)((ser, args.firmware)):
                logger.info("All OK")
            else:
                logger.error("Exiting on error")
        except ValueError, ex:
            logger.error(ex.message)
    else:
        parser.print_usage()


if __name__ == '__main__':
    logger = log.fuct_logger('fuctlog')
    main()