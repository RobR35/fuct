# -*- coding: utf-8 -*-
#
# This file is part of fuct. Copyright (c) 2014 Ari Karhu.
# See the LICENSE file for license rights and limitations (MIT).
#

__author__ = 'ari'

import struct


class Protocol(object):
    # Commands
    FE_CMD_RAM_WRITE = 0x0100
    FE_CMD_FLASH_WRITE = 0x0102
    FE_CMD_RAM_READ = 0x0104
    FE_CMD_FLASH_READ = 0x0106

    FE_CMD_INTERFACE = 0x0000
    FE_CMD_FIRMWARE = 0x0002
    FE_CMD_DATALOG_DESC = 0x0300
    FE_CMD_LOCATION_ID_LIST = 0xDA5E
    FE_CMD_LOCATION_ID_INFO = 0xF8E0
    FE_CMD_DECODER = 0xEEEE
    FE_CMD_BUILDDATE = 0xEEF0
    FE_CMD_COMPILER = 0xEEF2
    FE_CMD_OSNAME = 0xEEF4
    FE_CMD_USER = 0xEEF6
    FE_CMD_EMAIL = 0xEEF8

    # RAM Locations (location id, offset)
    FE_LOCATION_STREAM = (0x9000, 0x0000)  # 1 byte, 0 = disable, 1 = enable
    FE_LOCATION_TRIGGER = (0xC003, 0x0060)  # 2 bytes

    @staticmethod
    def create_packet(payload, location=None, size=None, data=None, use_length=False):

        # -----
        beef = bytearray()
        if location is not None:
            beef.extend(struct.pack('>HH', location[0], location[1]))

        if size is not None:
            beef.extend(struct.pack('>H', size))

        if data is not None:
            beef.extend(data)
        # -----
        beef_size = len(beef)
        msg = bytearray()

        if use_length and beef_size > 0:
            msg.append(0x01)
        else:
            msg.append(0x00)

        msg.extend(struct.pack('>H', payload))

        if use_length and beef_size > 0:
            msg.extend(struct.pack('>H', beef_size))

        if beef_size > 0:
            msg.extend(beef)

        checksum = sum(msg) & 0xff
        msg.append(checksum)

        msg = Protocol.escape_packet(msg)
        msg.insert(0, 0xAA)
        msg.append(0xCC)

        return msg

    @staticmethod
    def escape_packet(data):
        edata = bytearray()
        for c in data:
            if c == 0xAA:
                edata.extend(b'\xBB\x55')
            elif c == 0xBB:
                edata.extend(b'\xBB\x44')
            elif c == 0xCC:
                edata.extend(b'\xBB\x33')
            else:
                edata.append(c)
        return edata

    @staticmethod
    def decode_packet(data):
        flags = data[0]
        payload = (data[1] << 8) + data[2]
        length = 0
        if flags == 0x01:
            length = (data[3] << 8) + data[4]

        if length > 0:
            return payload, data[5:(length + 5)]
        else:
            return payload, None
