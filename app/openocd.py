#!/user/bin/env python3

"""
Connect to OpenOCD via Telnet
"""

import telnetlib


class OpenOCDTelnet:
    def __init__(self):
        self.is_opened = False

    def open(self, host="localhost", port=4444, timeout=1):
        self.telnet = telnetlib.Telnet(host, port)
        self.is_opened = True
        self.timeout = timeout
        self.read_data()

    def close(self):
        self.telnet.close()

    def check_alive(self):
        try:
            if self.telnet.sock:
                self.telnet.sock.sendall(telnetlib.IAC + telnetlib.NOP)
                self.telnet.sock.sendall(telnetlib.IAC + telnetlib.NOP)
                self.telnet.sock.sendall(telnetlib.IAC + telnetlib.NOP)
            return True
        except:
            self.close()
            self.is_opened = False
            return False

    def read_data(self):
        if self.is_opened:
            return self.telnet.read_until(b"\r\n\r", self.timeout).decode()
        else:
            raise RuntimeError("Can't read data - OpenOCD telnet is not opened!")

    def write_data(self, data):
        if self.is_opened:
            self.telnet.write(("%s\r\n" % data).encode())
        else:
            raise RuntimeError("Can't write data - OpenOCD telnet is not opened!")

    def send_cmd(self, cmd):
        self.write_data(cmd)
        return self.read_data().split('\n')[1].strip()

    def get_target_name(self):
        return self.send_cmd("target current")

    def read_mem(self, addr):
        return int(self.send_cmd("mdw 0x%08x" % addr).split(":")[1].strip(), 16)

    def write_mem(self, addr, val):
        self.send_cmd("mww 0x%08x 0x%08x" % (addr, val))


if __name__ == "__main__":
    openocd_tn = OpenOCDTelnet()
    openocd_tn.open()
    print(openocd_tn.get_target_name())
    input("Press any key to exit...")
