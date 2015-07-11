# -*- coding: utf-8 -*-
#
# This file is part of fuct. Copyright (c) 2014 Ari Karhu.
# See the LICENSE file for license rights and limitations (MIT).
#

__author__ = 'ari'

import threading
import Queue
import log
import time

LOG = log.fuct_logger('fuctlog')


class RxThread(threading.Thread):
    def __init__(self, ser, queue_in, queue_log):
        super(RxThread, self).__init__()
        self.ser = ser
        self.queue_in = queue_in
        self.queue_log = queue_log
        self.logging = False
        self.active = True

    def stop(self):
        self.active = False

    def run(self):
        in_packet = False
        in_escape = False
        outbuf = bytearray()

        while self.active:

            # Incoming
            buf = self.ser.read(1024)

            for c in buf:
                if ord(c) == 0xAA:
                    if in_packet:
                        """ Start byte in the middle of a packet, start fresh """
                        in_escape = False
                        outbuf = bytearray()

                    in_packet = True

                elif ord(c) == 0xCC and in_packet:
                    in_packet = False

                    size = len(outbuf)
                    flags = outbuf[0]
                    payload = (outbuf[1] << 8) + outbuf[2]
                    length = 0
                    if flags == 0x01:
                        length = (outbuf[3] << 8) + outbuf[4]
                    checksum1 = outbuf.pop()

                    # Check checksum
                    checksum2 = sum(outbuf) & 0xff
                    if (size == length + 5) or (checksum1 == checksum2):
                        if payload == 0x191:  # log packet
                            try:
                                if self.logging:
                                    self.queue_log.put(outbuf[5:], False)
                            except Queue.Full:
                                # TODO: log queue overflow situations
                                pass
                        else:
                            self.queue_in.put(outbuf)

                    outbuf = bytearray()

                else:
                    if in_packet and not in_escape:
                        """ Escape next byte """
                        if ord(c) == 0xBB:
                            in_escape = True
                        else:
                            outbuf += c

                    elif in_packet and in_escape:
                        if ord(c) == 0x55:
                            outbuf += chr(0xAA)
                        elif ord(c) == 0x44:
                            outbuf += chr(0xBB)
                        elif ord(c) == 0x33:
                            outbuf += chr(0xCC)

                        in_escape = False