#!/user/bin/env python3

"""
Read SVD file with cmsic-svd backend
"""

from operator import itemgetter
from cmsis_svd.parser import SVDParser
from cmsis_svd.parser import pkg_resources


class SVDReader:
    def __init__(self):
        self.device = []

    def get_packed_list(self):
        packed = []
        vendors = pkg_resources.resource_listdir("cmsis_svd", "data")
        for vendor in vendors:
            filenames = [n for n in pkg_resources.resource_listdir("cmsis_svd", "data/%s" % vendor) if ".svd" in n]
            packed += [{"vendor": vendor,
                        "filenames": sorted(filenames)}]
        return sorted(packed, key=lambda k: k['vendor'])

    def parse_path(self, path):
        self.__fill_device([periph for periph in SVDParser.for_xml_file(path).get_device().peripherals])

    def parse_packed(self, vendor, filename):
        self.__fill_device([periph for periph in SVDParser.for_packaged_svd(vendor, filename).get_device().peripherals])

    def __fill_device(self, peripherals):
        # Read peripherals and their registers
        self.device = []
        for periph in peripherals:
            self.device += [{"type": "periph",
                             "name": periph.name,
                             "description": periph.description,
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
                                                 "description": reg.description,
                                                 "address_offset": reg.address_offset,
                                                 "fields": []}]
                    for field in reg.fields:
                        self.device[-1]["regs"][-1]["fields"] += [{"type": "field",
                                                                   "name": field.name,
                                                                   "description": field.description,
                                                                   "address_offset": reg.address_offset,
                                                                   "lsb": field.bit_offset,
                                                                   "msb": field.bit_offset + field.bit_width - 1,
                                                                   "access": field.access,
                                                                   "enums": None}]
                        if field.enumerated_values:
                            self.device[-1]["regs"][-1]["fields"][-1]["enums"] = []
                            for enum in field.enumerated_values:
                                self.device[-1]["regs"][-1]["fields"][-1]["enums"] += [{"name": enum.name,
                                                                                        "description": enum.description,
                                                                                        "value": enum.value}]
            self.device[-1]["regs"] = sorted(self.device[-1]["regs"], key=itemgetter('address_offset'))
        self.device = sorted(self.device, key=itemgetter('base_address'))


if __name__ == "__main__":
    from pprint import pprint

    svd_reader = SVDReader()
    pprint(svd_reader.get_packed_list())
    svd_reader.parse_packed('STMicro', 'STM32F103xx.svd')
    for periph in svd_reader.device:
        pprint(periph["name"])
