# -*- coding: utf-8 -*-
#
# This file is part of fuct. Copyright (c) 2014 Ari Karhu.
# See the LICENSE file for license rights and limitations (MIT).
#

__author__ = 'ari'

import logging

LOG = logging.getLogger('fuctlog')


class MemoryPage:
    MAXSIZE = 16384

    def __init__(self, page, address, data=None):
        self.page = page
        self.address = address
        self.data = data

    def add_data(self, data):
        if self.data is None:
            self.data = data
        else:
            self.data += data


def records_to_pages(records):
    pages = []
    page = None
    last_addr = curr_page = 0
    total_size = 0

    for rec in records:
        if rec.stype[0] == 'S2':
            rpage = rec.get_page()
            address = rec.get_page_address()
            rec_size = len(rec.data)
            if rec_size:
                if rpage == curr_page and address == last_addr:
                    last_addr = add_to_page(page, rec.data, last_addr)
                else:
                    if page is not None:
                        pages.append(page)

                    page = MemoryPage(rpage, address)
                    curr_page = rpage
                    last_addr = add_to_page(page, rec.data, address)
                total_size += rec_size
            else:
                LOG.warning("Record has no data, skipping...")

        else:
            LOG.warning("%s records are not supported, skipping..." % rec.stype[0])

    pages.append(page)  # TODO: add to for loops last round

    return pages, total_size


def add_to_page(page, data, address):
    page.add_data(data)
    return address + len(data)