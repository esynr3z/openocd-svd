#!/user/bin/env python3

"""
Read SVD file with cmsic-svd backend
"""

import sys
from operator import itemgetter
from cmsis_svd.parser import SVDParser


class SVDReader:
    def __init__(self, path):
        parser = [periph for periph in SVDParser.for_xml_file(path).get_device().peripherals]

        # Read peripherals and their registers
        self.device = []
        for periph in parser:
            self.device += [{"name": periph.name,
                             "description": periph.description,
                             "base_address": periph.base_address,
                             "regs": periph.derived_from}]  # regs value will be replaced with regs list
            if (self.device[-1]["regs"] is not None):
                    self.device[-1]["regs"] = next(periph for periph in self.device if periph["name"] == self.device[-1]["regs"])["regs"].copy()
            else:
                self.device[-1]["regs"] = []
                for reg in periph.registers:
                    self.device[-1]["regs"] += [{"name": reg.name,
                                                 "description": reg.description,
                                                 "address_offset": reg.address_offset,
                                                 "fields": []}]
                    for field in reg.fields:
                        self.device[-1]["regs"][-1]["fields"] += [{"name": field.name,
                                                                   "description": field.description,
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

        self.device = sorted(self.device, key=itemgetter('base_address'))


if __name__ == "__main__":
    svd_file = SVDReader(sys.argv[1])
