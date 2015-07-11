# -*- coding: utf-8 -*-
#
# This file is part of fuct. Copyright (c) 2014 Ari Karhu.
# See the LICENSE file for license rights and limitations (MIT).
#

__author__ = 'ari'

import time
import binascii
import protocol
import struct
import Queue
import log

LOG = log.fuct_logger('fuctlog')


class Interrogator(object):

    def __init__(self, ser, queue_in, queue_out):
        self.ser = ser
        self.queue_in = queue_in
        self.queue_out = queue_out

    def run(self):
        meta_cmds = [
            ("interface", protocol.Protocol.FE_CMD_INTERFACE),
            ("firmware", protocol.Protocol.FE_CMD_FIRMWARE),
            ("decoder", protocol.Protocol.FE_CMD_DECODER),
            ("build_date", protocol.Protocol.FE_CMD_BUILDDATE),
            ("compiler", protocol.Protocol.FE_CMD_COMPILER),
            ("os", protocol.Protocol.FE_CMD_OSNAME),
            ("build_by", protocol.Protocol.FE_CMD_USER),
            ("email", protocol.Protocol.FE_CMD_EMAIL)
        ]

        meta = {}

        for _, cmd in meta_cmds:
            self.queue_out.put(protocol.Protocol.create_packet(cmd))

        #queue_out.put(protocol.Protocol.create_packet(protocol.Protocol.FE_CMD_LOCATION_ID_LIST, data=bytearray(b'\x00\x00\x00')))

        while True:
            if all(name in meta for name, _ in meta_cmds):
                break

            try:
                time.sleep(0.2)
                packet = self.queue_out.get(False)
                LOG.debug("--> %s" % binascii.hexlify(packet[1:-2]))
                self.ser.write(packet)
                self.ser.flush()
            except Queue.Empty:
                pass

            try:
                msg = self.queue_in.get(False)
                LOG.debug("<-- %s" % binascii.hexlify(msg))
                data = protocol.Protocol.decode_packet(msg)

                # FIXME: hax, make more elegant
                meta_info = [(name, data[1].decode("ascii").rstrip('\0')) for name, cmd_id in meta_cmds if cmd_id + 1 == data[0]][0]
                if meta_info:
                    LOG.info("Received meta: %s" % meta_info[0])
                    meta[meta_info[0]] = meta_info[1]

                elif data[0] == protocol.Protocol.FE_CMD_LOCATION_ID_LIST + 1:
                    LOG.info("Received location ID list")
                    locs = struct.unpack_from(">25H", data[1])
                    #for loc in locs:
                    #    queue_out.put(protocol.Protocol.create_packet(protocol.Protocol.FE_CMD_LOCATION_ID_INFO, data=struct.pack(">H", loc)))
                    #queue_out.put(protocol.Protocol.create_packet(protocol.Protocol.FE_CMD_LOCATION_ID_INFO, data=bytearray(b'\x90\x00')))
                elif data[0] == protocol.Protocol.FE_CMD_LOCATION_ID_INFO + 1:
                    LOG.info("Received location info")
                    print data
                    print binascii.hexlify(data[1])

            except Queue.Empty:
                pass

        return meta