#!/user/bin/env python3

"""
Read SVD file with cmsic-svd backend
"""

import os
from operator import itemgetter
import cmsis_svd
from cmsis_svd.parser import SVDParser


class SVDReader:
    def __init__(self):
        self.device = []

    def get_packed_list(self):
        packed = []
        data_path = os.path.join(cmsis_svd.__path__[0], "data")
        vendors = os.listdir(data_path)
        for vendor in vendors:
            vendor_path = os.path.join(data_path, vendor)
            filenames = [n for n in os.listdir(vendor_path) if ".svd" in n]
            packed += [{"vendor": vendor,
                        "filenames": sorted(filenames)}]
        return sorted(packed, key=lambda k: k['vendor'])

    def parse_path(self, path):
        self.__fill_device([periph for periph in SVDParser.for_xml_file(path).get_device().peripherals])

    def parse_packed(self, vendor, filename):
        self.parse_path(os.path.join(cmsis_svd.__path__[0], "data", vendor, filename))

    def __fill_device(self, peripherals):
        # Read peripherals and their registers
        self.device = []
        for periph in peripherals:
            self.device += [{"type": "periph",
                             "name": periph.name,
                             "description": self.__item_description(periph),
                             "base_address": periph.base_address,
                             "group_name": periph.group_name,
                             "regs": periph.derived_from}]  # regs value will be replaced with regs list
            if (self.device[-1]["regs"] is not None):
                    self.device[-1]["regs"] = next(periph for periph in self.device if periph["name"] == self.device[-1]["regs"])["regs"].copy()
            else:
                self.device[-1]["regs"] = []
                for reg in periph.registers:
                    self.device[-1]["regs"] += [{"type": "reg",
                                                 "name": reg.name,
                                                 "description": self.__item_description(reg),
                                                 "address_offset": reg.address_offset,
                                                 "fields": []}]
                    for field in reg.fields:
                        self.device[-1]["regs"][-1]["fields"] += [{"type": "field",
                                                                   "name": field.name,
                                                                   "description": self.__item_description(field),
                                                                   "address_offset": reg.address_offset,
                                                                   "lsb": field.bit_offset,
                                                                   "msb": field.bit_offset + field.bit_width - 1,
                                                                   "access": field.access,
                                                                   "enums": None}]
                        if field.enumerated_values:
                            self.device[-1]["regs"][-1]["fields"][-1]["enums"] = []
                            for enum in field.enumerated_values:
                                self.device[-1]["regs"][-1]["fields"][-1]["enums"] += [{"name": enum.name,
                                                                                        "description": self.__item_description(enum),
                                                                                        "value": enum.value}]
            self.device[-1]["regs"] = sorted(self.device[-1]["regs"], key=itemgetter('address_offset'))
        self.device = sorted(self.device, key=itemgetter('base_address'))

    def __item_description(self, item):
        if item.description:
            return ' '.join(item.description.replace("\n", " ").split())
        else:
            return "No description"


if __name__ == "__main__":
    from pprint import pprint

    svd_reader = SVDReader()
    pprint(svd_reader.get_packed_list())
    svd_reader.parse_packed('STMicro', 'STM32F103xx.svd')
    for periph in svd_reader.device:
        pprint(periph["name"])
