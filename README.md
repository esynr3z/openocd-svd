# openocd-svd

openocd-svd is a special Python utility to access peripheral registers of ARM MCUs via OpenOCD's telnet

## Dependencies

- python3+
- openocd
- pyqt5
- [cmsis-svd](https://github.com/posborne/cmsis-svd)

## How to use

- Start OpenOCD and connect your MCU
- Start openocd-svd and open SVD (CMSIS System View Description) file with peripheral register structure of your MCU ([cmis.arm.com](http://cmsis.arm.com/), [cmsis-svd](https://github.com/posborne/cmsis-svd))
- Press Connect to access OpenOCD via telnet interface (localhost 4444)
