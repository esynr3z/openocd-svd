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
from svd import SVDReader
from openocd import OpenOCDTelnet
from PyQt5 import QtCore
from PyQt5.QtGui import QCursor, QRegExpValidator, QIntValidator, QColor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDialog, QWidget, QComboBox, QCheckBox,
                             QFileDialog, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget,
                             QTreeWidgetItem, QLineEdit, QAction, QMenu, QPushButton, QSizePolicy)
from ui_main import Ui_MainWindow
from ui_about import Ui_Dialog
from ui_svd import Ui_SVDDialog


# -- Global variables ---------------------------------------------------------
VERSION = "0.5"


# -- Custom widgets -----------------------------------------------------------
class NumEdit(QLineEdit):
    def __init__(self, num_bwidth=32):
        QLineEdit.__init__(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.handle_context_menu_requested)
        self.__num_bwidth = num_bwidth
        self.__display_base = 16
        self.setText("0")
        self.setDisplayFormat(16)
        self.is_focused = False

    # -- Events --
    def focusInEvent(self, event):
        self.is_focused = True
        QLineEdit.focusInEvent(self, event)

    def focusOutEvent(self, event):
        self.is_focused = False
        QLineEdit.focusOutEvent(self, event)

    def wheelEvent(self, event):
        if self.is_focused:
            delta = 1 if event.angleDelta().y() > 0 else -1
            if 2**self.numBitWidth() > (self.num() + delta) >= 0:
                self.setNum(self.num() + delta)
            event.accept()
            self.editingFinished.emit()

    # -- Slots --
    def handle_context_menu_requested(self, pos):
        self.menu = self.createStandardContextMenu()

        self.menu.act_to_dec = QAction("Convert to Dec")
        self.menu.act_to_dec.triggered.connect(lambda: self.handle_act_convert_triggered(10))
        self.menu.act_to_hex = QAction("Convert to Hex")
        self.menu.act_to_hex.triggered.connect(lambda: self.handle_act_convert_triggered(16))
        self.menu.act_to_bin = QAction("Convert to Bin")
        self.menu.act_to_bin.triggered.connect(lambda: self.handle_act_convert_triggered(2))
        self.menu.insertActions(self.menu.actions()[0],
                                [self.menu.act_to_dec, self.menu.act_to_hex, self.menu.act_to_bin])
        self.menu.insertSeparator(self.menu.actions()[3])

        self.menu.exec_(QCursor.pos())

    def handle_act_convert_triggered(self, base):
        self.setDisplayFormat(base)

    # -- API --
    def numBitWidth(self):
        return self.__num_bwidth

    def setNumBitWidth(self, width):
        self.__num_bwidth = width

    def num(self):
        return int(self.text().replace(" ", ""), self.displayBase())

    def setNum(self, num, base=None):
        if base:
            self.setDisplayFormat(base, num)
        else:
            self.setDisplayFormat(self.displayBase(), num)

    def displayBase(self):
        return self.__display_base

    def setDisplayValidator(self, base):
        if base == 10:
            max_int = 2**self.numBitWidth()
            self.setValidator(QIntValidator(0, max_int - 1))
        elif base == 16:
            high_part = ""
            low_part = ""
            if self.numBitWidth() % 4 > 0:
                high_part = "[0-%d]" % (2**(self.numBitWidth() % 4) - 1)
            if int(self.numBitWidth() / 4) > 0:
                low_part = "[0-9A-Fa-f]{%d}" % int(self.numBitWidth() / 4)
            allowed_symbols = "0x" + high_part + low_part
            self.setValidator(QRegExpValidator(QtCore.QRegExp(allowed_symbols)))
        elif base == 2:
            high_part = ""
            low_part = ""
            if self.numBitWidth() % 4 > 0:
                high_part = "(0|1){%d}" % (self.numBitWidth() % 4)
            if int(self.numBitWidth() / 4) > 0:
                low_part = "((\s|)(0|1){4}){%d}" % int(self.numBitWidth() / 4)
            allowed_symbols = "^" + high_part + low_part + "$"
            self.setValidator(QRegExpValidator(QtCore.QRegExp(allowed_symbols)))

    def setDisplayFormat(self, base, num=None):
        if num is not None:
            self.setText(self.__format_num(num, base))
        else:
            self.setText(self.__format_num(self.num(), base))
        self.setDisplayValidator(base)
        self.__display_base = base

    def __format_num(self, num, base):
        if base == 10:
            return str(num)
        elif base == 16:
            return format(num, '#0%dx' % (2 + int(self.numBitWidth() / 4) + (self.numBitWidth() % 4 > 0)))
        elif base == 2:
            chunk_n = 4
            bin_str = format(num, '0%db' % self.numBitWidth())
            return ' '.join(([bin_str[::-1][i:i + chunk_n] for i in range(0, len(bin_str), chunk_n)]))[::-1]
        else:
            raise ValueError("Can't __format_num() - unknown base")


class RegEdit(QWidget):
    def __init__(self, svd_reg):
        QWidget.__init__(self)
        self.svd = svd_reg
        self.horiz_layout = QHBoxLayout(self)
        self.horiz_layout.setContentsMargins(0, 0, 0, 0)
        self.horiz_layout.setSpacing(0)
        self.nedit_val = NumEdit(32)
        self.nedit_val.editingFinished.connect(self.handle_reg_value_changed)
        self.nedit_val.setMinimumSize(QtCore.QSize(320, 20))
        self.nedit_val.setMaximumSize(QtCore.QSize(16777215, 20))
        self.nedit_val.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed))
        self.horiz_layout.addWidget(self.nedit_val)
        self.btn_read = QPushButton(self)
        self.btn_read.setText("R")
        self.btn_read.setMaximumSize(QtCore.QSize(25, 20))
        self.horiz_layout.addWidget(self.btn_read)
        self.btn_write = QPushButton(self)
        self.btn_write.setText("W")
        self.btn_write.setMaximumSize(QtCore.QSize(25, 20))
        self.horiz_layout.addWidget(self.btn_write)
        self.fields = {}
        for field in self.svd["fields"]:
            self.fields[field["name"]] = FieldEdit(field)
            self.fields[field["name"]].valueChanged.connect(self.handle_field_value_changed)

    # -- Slots --
    def handle_reg_value_changed(self):
        # if value changed we should set new fields values
        for key in self.fields.keys():
            val = self.val()
            val = (val >> self.fields[key].svd["lsb"]) & ((2 ** self.fields[key].num_bwidth) - 1)
            self.fields[key].setVal(val)

    def handle_field_value_changed(self):
        # if field value changed we should set update reg value
        val = self.val() & ~(((2 ** self.sender().num_bwidth) - 1) << self.sender().svd["lsb"])
        val = val | (self.sender().val() << self.sender().svd["lsb"])
        self.__update_val(val)

    # -- API --
    def val(self):
        return self.nedit_val.num()

    def __update_val(self, val):
        self.nedit_val.setNum(val)

    def setVal(self, val):
        self.__update_val(val)
        self.handle_reg_value_changed()


class FieldEdit(QWidget):
    valueChanged = QtCore.pyqtSignal()

    def __init__(self, svd_field):
        QWidget.__init__(self)
        self.svd = svd_field
        self.horiz_layout = QHBoxLayout(self)
        self.horiz_layout.setContentsMargins(0, 0, 0, 0)
        self.horiz_layout.setSpacing(6)
        if self.svd["access"] == "read-only":
            self.is_enabled = False
        else:
            self.is_enabled = True

        self.num_bwidth = self.svd["msb"] - self.svd["lsb"] + 1

        if self.num_bwidth == 1:
            self.chbox_val = QCheckBox(self)
            self.chbox_val.setEnabled(self.is_enabled)
            self.chbox_val.setMaximumSize(QtCore.QSize(16777215, 20))
            self.chbox_val.stateChanged.connect(self.handle_field_value_changed)
            self.horiz_layout.addWidget(self.chbox_val)
        else:
            self.nedit_val = NumEdit(self.num_bwidth)
            self.nedit_val.setEnabled(self.is_enabled)
            self.nedit_val.editingFinished.connect(self.handle_field_value_changed)
            self.nedit_val.setMaximumSize(QtCore.QSize(16777215, 20))
            self.horiz_layout.addWidget(self.nedit_val)

        if self.svd["enums"]:
            self.is_enums = True
            self.combo_enum = QComboBox(self)
            self.combo_enum.setEnabled(self.is_enabled)
            self.combo_enum.currentIndexChanged.connect(self.handle_enum_value_changed)
            self.combo_enum.values = []
            for enum in self.svd["enums"]:
                self.combo_enum.values += [int(enum["value"])]
                self.combo_enum.addItem("(0x%x) %s : %s" % (int(enum["value"]), enum["name"], enum["description"]))
            self.combo_enum.setMaximumSize(QtCore.QSize(16777215, 20))
            self.horiz_layout.addWidget(self.combo_enum)
            if self.num_bwidth == 1:
                self.chbox_val.setMaximumSize(QtCore.QSize(320, 20))
            else:
                self.nedit_val.setMaximumSize(QtCore.QSize(320, 20))
        else:
            self.is_enums = False

    # -- Slots --
    def handle_field_value_changed(self, value=None):
        if self.is_enums:
            try:
                if self.val() != self.combo_enum.values[self.combo_enum.currentIndex()]:
                    self.combo_enum.setCurrentIndex(self.combo_enum.values.index(self.val()))
            except ValueError:
                self.combo_enum.setCurrentIndex(-1)
        self.valueChanged.emit()

    def handle_enum_value_changed(self, currentIndex):
        if self.is_enums and currentIndex != -1:
            if self.val() != self.combo_enum.values[currentIndex]:
                self.setVal(self.combo_enum.values[currentIndex])

    # -- API --
    def val(self):
        if self.num_bwidth == 1:
            if self.chbox_val.checkState():
                return 1
            else:
                return 0
        else:
            return self.nedit_val.num()

    def setVal(self, val):
        if self.num_bwidth == 1:
            if val:
                self.chbox_val.setCheckState(QtCore.Qt.Checked)
            else:
                self.chbox_val.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.nedit_val.setNum(val)
        self.handle_field_value_changed()


class PeriphTab(QWidget):
    def __init__(self, svd_periph):
        QWidget.__init__(self)
        self.svd = svd_periph
        self.setObjectName(self.svd["name"])
        # vertical layout inside
        self.vert_layout = QVBoxLayout(self)
        self.vert_layout.setContentsMargins(6, 6, 6, 6)
        self.vert_layout.setSpacing(6)
        # label with peripheral description
        self.lab_periph_descr = QLabel(self)
        self.lab_periph_descr.setText(self.svd["description"])
        self.lab_periph_descr.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse |
                                                      QtCore.Qt.TextSelectableByMouse)
        self.vert_layout.addWidget(self.lab_periph_descr)
        # tree widget for displaying regs
        reg_col = 0
        val_col = 1
        self.tree_regs = QTreeWidget(self)
        self.tree_regs.itemSelectionChanged.connect(self.handle_tree_selection_changed)
        self.tree_regs.headerItem().setText(reg_col, "Register")
        self.tree_regs.setColumnWidth(reg_col, 200)
        self.tree_regs.headerItem().setText(val_col, "Value")
        for reg in self.svd["regs"]:
            item0 = QTreeWidgetItem(self.tree_regs)
            item0.svd = reg
            item0.setText(reg_col, reg["name"])
            background = QColor(240, 240, 240)
            item0.setBackground(0, background)
            item0.setBackground(1, background)
            reg_edit = RegEdit(reg)
            self.tree_regs.setItemWidget(item0, val_col, reg_edit)
            self.tree_regs.addTopLevelItem(item0)
            for field in reg["fields"]:
                item1 = QTreeWidgetItem(item0)
                item1.svd = field
                item1.setText(reg_col, field["name"])
                self.tree_regs.setItemWidget(item1, val_col, reg_edit.fields[field["name"]])
                item0.addChild(item1)
        self.vert_layout.addWidget(self.tree_regs)
        # label with register/field description
        self.lab_info = QLabel(self)
        self.lab_info.setMaximumSize(QtCore.QSize(16777215, 40))
        self.lab_info.setMinimumSize(QtCore.QSize(16777215, 40))
        self.lab_info.setText("")
        self.lab_info.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse |
                                              QtCore.Qt.TextSelectableByMouse)
        self.vert_layout.addWidget(self.lab_info)

    # -- Slots --
    def handle_tree_selection_changed(self):
        tree_item = self.tree_regs.selectedItems()[0]
        name = tree_item.svd["name"]
        descr = tree_item.svd["description"]
        addr = tree_item.svd["address_offset"]
        if "access" in tree_item.svd.keys() and tree_item.svd["access"]:
            temp = tree_item.svd["access"]
            access = "<%s>" % (temp.split("-")[0][0] + temp.split("-")[1][0]).upper()
        else:
            access = ""
        if "msb" in tree_item.svd.keys():
            bits = "[%d:%d]" % (tree_item.svd["msb"],
                                tree_item.svd["lsb"])
        else:
            bits = ""
        self.lab_info.setText("(0x%08x)%s%s : %s\n%s" % (addr, bits, access, name, descr))


# -- Main window --------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        # Set up the user interface from QtDesigner
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Modify UI
        self.ui.act_periph = []
        self.ui.menu_periph = []
        self.ui.lab_status = QLabel()
        self.ui.lab_status.setText("No connection")
        self.ui.statusBar.addPermanentWidget(self.ui.lab_status)
        self.about_dialog = QDialog(self)
        self.about_dialog.ui = Ui_Dialog()
        self.about_dialog.ui.setupUi(self.about_dialog)
        self.svd_dialog = QDialog(self)
        self.svd_dialog.ui = Ui_SVDDialog()
        self.svd_dialog.ui.setupUi(self.svd_dialog)
        self.svd_dialog.ui.tree_svd.itemDoubleClicked.connect(self.handle_svd_dialog_item_double_clicked)
        self.svd_dialog.ui.tree_svd.headerItem().setText(0, "List of packed SVD")

        # Add some vars
        self.svd_reader = SVDReader()
        self.openocd_tn = OpenOCDTelnet()

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
            self.openocd_tn.is_opened = True
            self.ui.act_connect.setText("Disconnect OpenOCD")
            self.ui.lab_status.setText("Connected to %s" % self.openocd_tn.get_target_name())
        except:
            self.ui.statusBar.showMessage("Can't connect to OpenOCD!")

    def disconnect_openocd(self):
        self.openocd_tn.close()
        self.openocd_tn.is_opened = False
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
