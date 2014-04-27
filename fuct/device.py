__author__ = 'ari'

import sys
import logging
import binascii
import hashlib
from time import sleep
from struct import pack, unpack_from

logger = logging.getLogger('fuctlog')


class SMResponse():
    def __init__(self, response, status, data=None):
        self.response_code = response
        self.status_code = status
        self.data = data[:]  # Copy data

    def __str__(self):
        return "SM response %d, status %d, data %d bytes" % (self.response_code, self.status_code, len(self.data))


class Device():

    # Serial monitor characters
    SM_OPEN = 0x0D  # Carriage return
    SM_PROMPT = 0x3E  # > Prompt symbol
    SM_PPAGE = 0x30  # 0

    SM_DEVICE_IDX = 0x06F8
    SM_MONTH_IDX = 0x06FA
    SM_DAY_IDX = 0x06FB
    SM_YEAR_IDX = 0x06FC
    SM_VERSION_IDX = 0x06FE

    # Commands
    CMD_READ_BYTE = 0xA1
    CMD_WRITE_BYTE = 0xA2
    CMD_READ_WORD = 0xA3
    CMD_WRITE_WORD = 0xA4
    CMD_READ_NEXT = 0xA5
    CMD_WRITE_NEXT = 0xA6
    CMD_READ_BLOCK = 0xA7
    CMD_WRITE_BLOCK = 0xA8
    CMD_READ_REGS = 0xA9
    CMD_WRITE_SP = 0xAA
    CMD_WRITE_PC = 0xAB
    CMD_WRITE_IY = 0xAC
    CMD_WRITE_IX = 0xAD
    CMD_WRITE_D = 0xAE
    CMD_WRITE_CCR = 0xAF

    CMD_GO = 0xB1
    CMD_TRACE_ONE = 0xB2
    CMD_HALT = 0xB3
    CMD_RESET = 0xB4
    CMD_ERASE_RANGE = 0xB5  # Not supported by SM
    CMD_ERASE_ALL = 0xB6
    CMD_DEVICE_INFO = 0xB7
    CMD_ERASE_PAGE = 0xB8
    CMD_ERASE_EEPROM = 0xB9

    # Response codes
    RC_NO_ERROR = 0xE0
    RC_NOT_RECOGNISED = 0xE1
    RC_NOT_ALLOWED_IN_RUN_MODE = 0xE2
    RC_STACK_POINTER_OUT_OF_RANGE = 0xE3
    RC_INVALID_SP_VALUE = 0xE4
    RC_ACCESS_TO_NON_VOLATILE = 0xE5
    RC_FLASH_ERROR = 0xE6
    # 0xE7 and 0xE8 not implemented
    RC_EEPROM_ERROR = 0xE9

    # Status codes
    SC_MONITOR_ACTIVE = 0x00
    SC_USER_PROGRAM_RUNNING = 0x01
    SC_USER_PROGRAM_HALTED = 0x02
    SC_TRACE_ONE_RETURNED = 0x04
    SC_COLD_RESET_EXECUTED = 0x08
    SC_WARM_RESET_EXECUTED = 0x0C

    # Misc
    DEVICE_INFO_CONSTANT = 0xDC
    BLOCK_SIZE = 256

    # SM versions TODO: add more versions
    SM_VERSIONS = {
        'e886a55bf927f9c86cad5d26ca41ba88': 'Motorola SM v2.2 (with USB hack)'
    }

    def __init__(self, ser):
        self.ser = ser
        self.ns_per_byte = 86805

    # Highlevel commands

    @property
    def check_device(self):  # TODO: maybe return some device info
        resp = self.device_info()
        if ord(resp.data[0]) == self.DEVICE_INFO_CONSTANT:
            if ord(resp.data[1]) == 0xC4 and ord(resp.data[2]) == 0x10:  # TODO: check more device ids
                logger.info("Device is S12 XDP512")
                return True

        logger.error("Device (C: 0x%02x, ID: 0x%02x%02x) is not supported" %
                     (ord(resp.data[0]), ord(resp.data[1]), ord(resp.data[2])))
        return False

    def analyse_device(self):
        addr = 0xF800
        smdata = bytearray()
        for page in range(0, 8):
            resp = self.__read_block(addr, 0xFF)
            smdata += resp.data
            addr += 256

        if len(smdata) != 2048:
            raise ValueError('Invalid SM size (%d bytes), should be 2k' % len(smdata))

        m = hashlib.md5()
        m.update(smdata)
        hash = binascii.hexlify(m.digest())
        logger.debug('SM MD5: %s' % hash)
        info = self.SM_VERSIONS.get(hash)
        if info is not None:
            logger.info('SM Identified as: %s' % info)
        else:
            logger.warning('SM is not recognized')

        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.debug('SM Device ID: 0x%02x%02x' % (smdata[self.SM_DEVICE_IDX], smdata[self.SM_DEVICE_IDX + 1]))
            logger.debug('SM Date: %02x/%02x/%02x%02x' %
                        (smdata[self.SM_MONTH_IDX], smdata[self.SM_DAY_IDX], smdata[self.SM_YEAR_IDX], smdata[self.SM_YEAR_IDX + 1]))
            logger.debug('SM Version: %x.%x' % (smdata[self.SM_VERSION_IDX], smdata[self.SM_VERSION_IDX + 1]))

        return True

    def erase_and_write(self, mempage, erase=True, verify=True):
        if mempage.address < 0x8000 or mempage.address >= 0xC000:
            raise ValueError('Address %d is out of range for page %d' % (mempage.address, mempage.page))

        if len(mempage.data) > 0xC000 - mempage.address:
            raise ValueError('Invalid amount of data (%d bytes), will overflow page %d @ %d' %
                             (len(mempage.data), mempage.page, mempage.address))

        if erase:
            self.write_page(mempage.page)
            self.erase_page()

        blocks = len(mempage.data) / self.BLOCK_SIZE
        trailing = len(mempage.data) % self.BLOCK_SIZE
        start_block = 0
        start_addr = mempage.address

        for block in range(0, blocks):
            block_data = mempage.data[start_block:start_block + self.BLOCK_SIZE]
            start_block += self.BLOCK_SIZE

            self.__write_block(start_addr, block_data)

            if verify:  # TODO: do verification
                pass

            start_addr += self.BLOCK_SIZE

        if trailing > 0:  # TODO: add trailing write to for loop and verify
            block_data = mempage.data[-trailing:]
            self.__write_block(start_addr, block_data)

    def erase_pages(self, start, end):
        total = end - start
        last = end + 1
        counter = 0
        for page in xrange(start, last):
            self.write_page(page)
            self.erase_page()
            if logger.getEffectiveLevel() == logging.INFO:
                sys.stdout.write("\r[%3d%%]" % ((float(counter) / float(total)) * 100))
                sys.stdout.flush()
            counter += 1
        logging.info("Done")

        return True

    def write_page(self, page):
        self.__write_byte(self.SM_PPAGE, page)

    # Lowlevel commands

    def reset(self):
        self.__write_command(self.CMD_RESET)
        rdata = self.__get_data_after_wait(5, 2)
        if len(rdata) <= 1:
            return SMResponse(None, None, rdata)

    def open_comm(self):
        self.__write_command(self.SM_OPEN)
        rdata = self.__get_data_after_wait(4)
        if len(rdata) == 3:
            return self.__check_open_response(rdata)
        elif len(rdata) == 4:
            return self.__check_open_response(rdata, 1)

    def reinit(self):
        self.reset()
        return self.open_comm()

    def device_info(self):
        return self.__write_standard(6, self.CMD_DEVICE_INFO)

    def erase_page(self):
        return self.__write_standard(3, self.CMD_ERASE_PAGE, 330)

    # Privates

    @staticmethod
    def __get_addr_data(addr, data):
        return pack('>HB', int(addr), data)

    def __write_command(self, cmd, args=None):
        self.ser.flushInput()
        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.debug("--> 0x%02x" % cmd)
        self.ser.write(chr(cmd))
        if args is not None:
            if logger.getEffectiveLevel() == logging.DEBUG:
                logger.debug("--> %s" % binascii.hexlify(args))
            self.ser.write(args)

    def __write_byte(self, addr, byte):
        args = self.__get_addr_data(addr, byte)
        return self.__write_standard(3, self.CMD_WRITE_BYTE, 0, args)

    def __read_block(self, addr, length):
        return self.__write_standard(length + 4, self.CMD_READ_BLOCK, 0, self.__get_addr_data(addr, length))

    def __write_block(self, addr, data):
        if len(data) > self.BLOCK_SIZE:
            raise ValueError("Block has %d bytes, needs to be 256 bytes or less" % len(data))

        args = self.__get_addr_data(addr, len(data) - 1)
        args += data

        return self.__write_standard(3, self.CMD_WRITE_BLOCK, -16, args)

    def __write_standard(self, resp_length, command, extra_sleep=0, args=None):
        if resp_length < 3:
            raise ValueError('Response for command %d must have at least 3 bytes' % command)

        self.__write_command(command, args)

        offset = resp_length - 3
        sent_bytes = 1 if args is None else len(args) + 1
        total_bytes = sent_bytes + resp_length
        rdata = self.__get_data_after_wait(total_bytes, extra_sleep)

        return self.__check_valid_response(rdata, offset if len(rdata) == resp_length else 0)

    def __get_data_after_wait(self, total_bytes, extra_millis=0):
        pre_sleep = float(total_bytes * self.ns_per_byte / 1000000) + extra_millis
        to_sleep = pre_sleep if pre_sleep > 1 else 1
        sleep(to_sleep / 1000)

        data = self.ser.read(total_bytes)
        if logger.getEffectiveLevel() == logging.DEBUG and len(data) > 0:
            logger.debug("<-- %s" % binascii.hexlify(data))

        return data

    def __check_open_response(self, data, offset=0):
        if len(data) < 3:
            raise ValueError('Invalid open response (too few bytes)')

        if ord(data[offset + 2]) == self.SM_PROMPT:
            rc = ord(data[offset])
            sc = ord(data[offset + 1])
            if rc == self.RC_NO_ERROR and sc == self.SC_COLD_RESET_EXECUTED:
                return SMResponse(self.RC_NO_ERROR, self.SC_COLD_RESET_EXECUTED, data)
            elif rc == self.RC_NOT_RECOGNISED and sc == self.SC_MONITOR_ACTIVE:
                return SMResponse(self.RC_NOT_RECOGNISED, self.SC_MONITOR_ACTIVE, data)
            raise ValueError('Invalid open response (RC: 0x%02x, SC: 0x%02x)' % (rc, sc))

        raise ValueError('Invalid open response (no prompt), is device in load/SM mode?')

    def __check_valid_response(self, data, offset):
        if len(data) < offset + 3:
            raise ValueError('Invalid response (too few bytes)')

        if ord(data[offset + 2]) == self.SM_PROMPT:
            rc = ord(data[offset])
            if rc == self.RC_NOT_RECOGNISED:
                raise ValueError('Invalid response (unrecognized command 0x%02x)' % rc)
            elif rc == self.RC_NO_ERROR:
                sc = ord(data[offset + 1])
                if sc == self.SC_MONITOR_ACTIVE:
                    return SMResponse(rc, sc, data[:-3])
                raise ValueError('Invalid response (RC: 0x%02x, SC: 0x%02x)' % (rc, sc))

        raise ValueError('Invalid response (no prompt)')
