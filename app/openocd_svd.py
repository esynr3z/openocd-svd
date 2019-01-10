#!/user/bin/env python3

"""
openocd-svd is a special Python GUI utility to access peripheral registers
of ARM MCUs via OpenOCD's telnet

Run (SVD path argument is optional):
    python3 openocd_svd.py %svd_file_path%
"""

# -- Imports ------------------------------------------------------------------
import sys
import os
import functools
import threading
import time
from svd import SVDReader
from openocd import OpenOCDTelnet
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDialog, QWidget,
                             QFileDialog, QLabel, QTreeWidgetItem, QAction, QMenu)
from ui_widgets import PeriphTab
from ui_main import Ui_MainWindow
from ui_about import Ui_AboutDialog
from ui_svd import Ui_SVDDialog


# -- Global variables ---------------------------------------------------------
VERSION = "1.0"


# -- Special classes ----------------------------------------------------------
class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.is_executing = False
        self.next_call = time.time()
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.is_executing = True
        self.function(*self.args, **self.kwargs)
        self.is_executing = False

    def start(self):
        if not self.is_running:
            self.next_call += self.interval
            self._timer = threading.Timer(self.next_call - time.time(), self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


# -- Main window --------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        # Set up the user interface from QtDesigner
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.act_periph = []
        self.ui.menu_periph = []
        self.ui.lab_status = QLabel()
        self.ui.lab_status.setText("No connection")
        self.ui.statusBar.addPermanentWidget(self.ui.lab_status)

        self.about_dialog = QDialog(self)
        self.about_dialog.ui = Ui_AboutDialog()
        self.about_dialog.ui.setupUi(self.about_dialog)

        self.svd_dialog = QDialog(self)
        self.svd_dialog.ui = Ui_SVDDialog()
        self.svd_dialog.ui.setupUi(self.svd_dialog)
        self.svd_dialog.ui.tree_svd.itemDoubleClicked.connect(self.handle_svd_dialog_item_double_clicked)
        self.svd_dialog.ui.tree_svd.headerItem().setText(0, "List of packed SVD")

        # Add some vars
        self.svd_reader = SVDReader()
        self.openocd_tn = OpenOCDTelnet()
        self.openocd_rt = None
        self.opt_autoread = False

    # -- Events --
    def closeEvent(self, event):
        if self.openocd_tn.is_opened:
            self.disconnect_openocd()
        event.accept()

    # -- Slots --
    def handle_act_connect_triggered(self):
        if self.openocd_tn.is_opened:
            self.disconnect_openocd()
        else:
            self.connect_openocd()

    def handle_act_open_svd_triggered(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,
                                                  "Open SVD file", "", "SVD Files (*.svd *.SVD *.xml)",
                                                  options=options)
        if fileName:
            self.open_svd_path(fileName)

    def handle_act_open_packed_svd_triggered(self):
        self.svd_dialog.ui.tree_svd.clear()
        for vendor in self.svd_reader.get_packed_list():
            vendor_name = vendor["vendor"]
            item0 = QTreeWidgetItem(self.svd_dialog.ui.tree_svd)
            item0.setText(0, vendor_name)
            item0.is_vendor = True
            self.svd_dialog.ui.tree_svd.addTopLevelItem(item0)
            for filename in vendor["filenames"]:
                item1 = QTreeWidgetItem(item0)
                item1.is_vendor = False
                item1.setText(0, filename)
                item0.addChild(item1)
        if self.svd_dialog.exec_() and (not self.svd_dialog.ui.tree_svd.currentItem().is_vendor):
            vendor = self.svd_dialog.ui.tree_svd.currentItem().parent().text(0)
            filename = self.svd_dialog.ui.tree_svd.currentItem().text(0)
            self.open_svd_packed(vendor, filename)

    def handle_svd_dialog_item_double_clicked(self, item, col):
        if not item.is_vendor:
            vendor = item.parent().text(0)
            filename = item.text(0)
            self.open_svd_packed(vendor, filename)
            self.svd_dialog.accept()

    def handle_act_about_triggered(self):
        text = self.about_dialog.ui.lab_version.text().replace("x.x", VERSION)
        self.about_dialog.ui.lab_version.setText(text)
        self.about_dialog.exec_()

    def handle_act_periph_triggered(self):
        sender_name = self.sender().objectName()
        for periph in self.svd_reader.device:
            if sender_name == periph["name"]:
                periph_num = self.svd_reader.device.index(periph)
                periph_name = self.svd_reader.device[periph_num]["name"]
                break

        if (self.ui.tabs_device.findChild(QWidget, periph_name)):
            self.ui.tabs_device.setCurrentWidget(self.ui.tabs_device.findChild(QWidget, periph_name))
        else:
            periph_tab = PeriphTab(self.svd_reader.device[periph_num])
            for i in range(0, periph_tab.tree_regs.topLevelItemCount()):
                reg = periph_tab.tree_regs.itemWidget(periph_tab.tree_regs.topLevelItem(i), 1)
                reg.btn_read.clicked.connect(functools.partial(self.handle_btn_read_clicked, index=i))
                reg.btn_write.clicked.connect(functools.partial(self.handle_btn_write_clicked, index=i))
            self.ui.tabs_device.addTab(periph_tab, periph_name)
            self.ui.tabs_device.setCurrentIndex(self.ui.tabs_device.count() - 1)

    def handle_btn_read_clicked(self, index):
        if self.openocd_tn.is_opened:
            periph = self.ui.tabs_device.currentWidget()
            reg = periph.tree_regs.itemWidget(periph.tree_regs.topLevelItem(index), 1)
            addr = periph.svd["base_address"] + reg.svd["address_offset"]
            try:
                reg.setVal(self.openocd_tn.read_mem(addr))
                self.ui.statusBar.showMessage("Read %s.%s @ 0x%08X - OK" % (periph.svd["name"],
                                                                            reg.svd["name"],
                                                                            addr))
            except RuntimeError:
                self.ui.statusBar.showMessage("Read %s.%s @ 0x%08X - Error" % (periph.svd["name"],
                                                                               reg.svd["name"],
                                                                               addr))

    def handle_btn_write_clicked(self, index):
        if self.openocd_tn.is_opened:
            periph = self.ui.tabs_device.currentWidget()
            reg = periph.tree_regs.itemWidget(periph.tree_regs.topLevelItem(index), 1)
            addr = periph.svd["base_address"] + reg.svd["address_offset"]
            try:
                self.openocd_tn.write_mem(addr, reg.val())
                self.ui.statusBar.showMessage("Write %s.%s @ 0x%08X - OK" % (periph.svd["name"],
                                                                             reg.svd["name"],
                                                                             addr))

            except RuntimeError:
                self.ui.statusBar.showMessage("Write %s.%s @ 0x%08X - Error" % (periph.svd["name"],
                                                                                reg.svd["name"],
                                                                                addr))

    def handle_tab_periph_close(self, num):
        widget = self.ui.tabs_device.widget(num)
        if widget is not None:
            widget.deleteLater()
        self.ui.tabs_device.removeTab(num)

    def handle_act_autowrite_toggled(self, state):
        for tab_n in range(0, self.ui.tabs_device.count()):
            tab = self.ui.tabs_device.widget(tab_n)
            for reg_n in range(0, tab.tree_regs.topLevelItemCount()):
                reg = tab.tree_regs.itemWidget(tab.tree_regs.topLevelItem(reg_n), 1)
                reg.setAutoWrite(state)

    def handle_act_autoread_toggled(self, state):
        self.opt_autoread = state

    # -- Application specific code --
    def close_svd(self):
        title = self.windowTitle()
        title = title.split(" - ")[-1]
        self.setWindowTitle(title)
        while self.ui.tabs_device.currentIndex() != -1:
            self.handle_tab_periph_close(self.ui.tabs_device.currentIndex())
        self.ui.menuView.clear()
        self.ui.menu_periph.clear()

    def open_svd_path(self, path):
        try:
            self.close_svd()
            self.svd_reader.parse_path(path)
            self.setWindowTitle(os.path.basename(path) + " - " + self.windowTitle())
            self.__update_menu_view()
        except:
            self.ui.statusBar.showMessage("Can't open %s - file is corrupted!" % os.path.basename(path))

    def open_svd_packed(self, vendor, filename):
        try:
            self.close_svd()
            self.svd_reader.parse_packed(vendor, filename)
            self.setWindowTitle(filename + " - " + self.windowTitle())
            self.__update_menu_view()
        except:
            self.ui.statusBar.showMessage("Can't open %s - file is corrupted!" % filename)

    def __update_menu_view(self):
        for periph in self.svd_reader.device:
                if periph["name"] == periph["group_name"]:
                    self.ui.act_periph += [QAction(self)]
                    self.ui.act_periph[-1].setObjectName(periph["name"])
                    self.ui.act_periph[-1].setText(periph["name"])
                    self.ui.act_periph[-1].triggered.connect(self.handle_act_periph_triggered)
                    self.ui.menuView.addAction(self.ui.act_periph[-1])
                else:
                    if periph["group_name"] in [menu.objectName() for menu in self.ui.menu_periph]:
                        menu_num = [menu.objectName() for menu in self.ui.menu_periph].index(periph["group_name"])
                    else:
                        self.ui.menu_periph += [QMenu(self.ui.menubar)]
                        menu_num = -1
                        self.ui.menu_periph[menu_num].setObjectName(periph["group_name"])
                        self.ui.menu_periph[menu_num].setTitle(periph["group_name"])
                        self.ui.menuView.addAction(self.ui.menu_periph[menu_num].menuAction())
                        self.ui.menu_periph[menu_num].act_periph = []
                    self.ui.menu_periph[menu_num].act_periph += [QAction(self)]
                    self.ui.menu_periph[menu_num].act_periph[-1].setObjectName(periph["name"])
                    self.ui.menu_periph[menu_num].act_periph[-1].setText(periph["name"])
                    self.ui.menu_periph[menu_num].act_periph[-1].triggered.connect(self.handle_act_periph_triggered)
                    self.ui.menu_periph[menu_num].addAction(self.ui.menu_periph[menu_num].act_periph[-1])

    def connect_openocd(self):
        try:
            self.openocd_tn.open()
            self.ui.act_connect.setText("Disconnect OpenOCD")
            self.openocd_target = self.openocd_tn.get_target_name()
            self.openocd_target_pc = self.openocd_tn.get_target_pc()
            self.__poll_openocd()
            self.openocd_rt = RepeatedTimer(1, self.__poll_openocd)
        except:
            self.ui.statusBar.showMessage("Can't connect to OpenOCD!")

    def __poll_openocd(self):
        if self.openocd_tn.check_alive():
            self.openocd_target_state = self.openocd_tn.get_target_state()
            if self.openocd_target_state != "halted":
                new_target_pc = self.openocd_target_pc
            else:
                new_target_pc = self.openocd_tn.get_target_pc()
            self.ui.lab_status.setText("Connected: %s | %s | 0x%08X" % (self.openocd_target,
                                                                        self.openocd_target_state, new_target_pc))
            if self.opt_autoread and self.ui.tabs_device.count():
                if ((self.openocd_target_state == "halted") and (new_target_pc != self.openocd_target_pc)):
                    self.ui.tabs_device.currentWidget().btn_readall.clicked.emit()
            self.openocd_target_pc = new_target_pc

        else:
            self.openocd_rt.is_executing = False
            self.disconnect_openocd()

    def disconnect_openocd(self):
        self.openocd_rt.stop()
        while self.openocd_rt.is_executing:
            pass
        self.openocd_tn.close()
        self.ui.act_connect.setText("Connect OpenOCD")
        self.ui.lab_status.setText("No connection")


# -- Standalone run -----------------------------------------------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    if len(sys.argv) > 1:
        main_window.open_svd_path(sys.argv[1])
    main_window.show()
    sys.exit(app.exec_())
