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
    FE_CMD_FIRMWARE = 0x0002
    FE_CMD_DECODER = 0xEEEE
    FE_CMD_BUILDDATE = 0xEEF0
    FE_CMD_COMPILER = 0xEEF2
    FE_CMD_OSNAME = 0xEEF4
    FE_CMD_USER = 0xEEF6
    FE_CMD_EMAIL = 0xEEF8

    # RAM Locations (location id, offset)
    #FE_LOCATION_STREAM = (0x9000, 0x0000)
    FE_LOCATION_TRIGGER = (0xC003, 0x0060)

    #FE_LOCATION_STREAM = bytearray([0x00, 0x01, 0x00, 0x90, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00])  # disable stream
    #FE_ENABLE_STREAM  = bytearray([0x00, 0x01, 0x00, 0x90, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01])  # enable stream
    #FE_TRIGGER_OFFSET = bytearray([0x01, 0x01, 0x02, 0x00, 0x08, 0xc0, 0x03, 0x00, 0x60, 0x00, 0x02, 0x00, 0x32])
    #FE_TRIGGER_OFFSET = bytearray([0x01, 0x01, 0x02, 0x00, 0x08, 0xc0, 0x03, 0x00, 0x60, 0x00, 0x02, 0xff, 0xcc])
    #FE_READ_TRIGGER = bytearray([0x00, 0x01, 0x06, 0xc0, 0x03, 0x00, 0x60, 0x00, 0x02])

    #     aa010106c003006000022dcc

    # +1: aa0101020008c00300600002003263cc
    # -1: aa0101020008c00300600002ffcefecc

    @staticmethod
    def create_packet(payload, location=None, size=None, data=None, use_length=False):

        # -----
        beef = bytearray()
        if location is not None:
            beef.extend(struct.pack('>H', location[0]))
            beef.extend(struct.pack('>H', location[1]))

        if size is not None:
            beef.extend(struct.pack('>H', size))

        elif data is not None:
            beef.extend(struct.pack('>H', len(data)))
            beef.extend(data)
        # -----
        beef_size = len(beef)

        msg = bytearray()
        msg.append(0xAA)

        if use_length and beef_size > 0:
            msg.append(0x01)
        else:
            msg.append(0x00)

        msg.extend(struct.pack('>H', payload))

        if use_length and beef_size > 0:
            msg.extend(struct.pack('>H', beef_size))

        if beef_size > 0:
            msg.extend(beef)

        checksum = sum(msg[1:]) & 0xff
        msg.append(checksum)
        msg.append(0xCC)

        return msg

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