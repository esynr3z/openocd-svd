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
from svd import SVDReader
from openocd import OpenOCDTelnet
from PyQt5 import QtCore
from PyQt5.QtGui import QCursor, QRegExpValidator, QIntValidator
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDialog, QWidget, QComboBox, QCheckBox,
                             QFileDialog, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget,
                             QTreeWidgetItem, QLineEdit, QAction, QMenu, QPushButton)
from ui_main import Ui_MainWindow
from ui_about import Ui_Dialog


# -- Global variables ---------------------------------------------------------
VERSION = "0.1"


# -- Custom widgets -----------------------------------------------------------
class NumEdit(QLineEdit):
    def __init__(self, numBitWidth=32):
        QLineEdit.__init__(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__contextMenu)
        self.__numBitWidth = numBitWidth
        self.__displayBase = 16
        self.setText("0")
        self.setDisplayFormat(16)

    def __contextMenu(self, pos):
        self.menu = self.createStandardContextMenu()

        self.menu.act_to_dec = QAction("Convert to Dec")
        self.menu.act_to_dec.triggered.connect(lambda: self.setDisplayFormat(10))
        self.menu.act_to_hex = QAction("Convert to Hex")
        self.menu.act_to_hex.triggered.connect(lambda: self.setDisplayFormat(16))
        self.menu.act_to_bin = QAction("Convert to Bin")
        self.menu.act_to_bin.triggered.connect(lambda: self.setDisplayFormat(2))
        self.menu.insertActions(self.menu.actions()[0],
                                [self.menu.act_to_dec, self.menu.act_to_hex, self.menu.act_to_bin])
        self.menu.insertSeparator(self.menu.actions()[3])

        self.menu.exec_(QCursor.pos())

    def numBitWidth(self):
        return self.__numBitWidth

    def setNumBitWidth(self, numBitWidth):
        self.__numBitWidth = numBitWidth

    def num(self):
        return int(self.text().replace(" ", ""), self.displayBase())

    def setNum(self, num, displayBase=None):
        if displayBase:
            self.setDisplayFormat(displayBase, num)
        else:
            self.setDisplayFormat(self.displayBase(), num)

    def displayBase(self):
        return self.__displayBase

    def setDisplayValidator(self, displayBase):
        if displayBase == 10:
            max_int = 2**self.numBitWidth()
            self.setValidator(QIntValidator(0, max_int - 1))
        elif displayBase == 16:
            high_part = ""
            low_part = ""
            if self.numBitWidth() % 4 > 0:
                high_part = "[0-%d]" % (2**(self.numBitWidth() % 4) - 1)
            if int(self.numBitWidth() / 4) > 0:
                low_part = "[0-9A-Fa-f]{%d}" % int(self.numBitWidth() / 4)
            allowed_symbols = "0x" + high_part + low_part
            self.setValidator(QRegExpValidator(QtCore.QRegExp(allowed_symbols)))
        elif displayBase == 2:
            high_part = ""
            low_part = ""
            if self.numBitWidth() % 4 > 0:
                high_part = "(0|1){%d}" % (self.numBitWidth() % 4)
            if int(self.numBitWidth() / 4) > 0:
                low_part = "((\s|)(0|1){4}){%d}" % int(self.numBitWidth() / 4)
            allowed_symbols = "^" + high_part + low_part + "$"
            self.setValidator(QRegExpValidator(QtCore.QRegExp(allowed_symbols)))

    def setDisplayFormat(self, displayBase, num=None):
        if num:
            self.setText(self.__formatNum(num, displayBase))
        else:
            self.setText(self.__formatNum(self.num(), displayBase))
        self.setDisplayValidator(displayBase)
        self.__displayBase = displayBase

    def __formatNum(self, num, base):
        if base == 10:
            return str(num)
        elif base == 16:
            return format(num, '#0%dx' % (2 + int(self.numBitWidth() / 4) + (self.numBitWidth() % 4 > 0)))
        elif base == 2:
            chunk_n = 4
            bin_str = format(num, '0%db' % self.numBitWidth())
            return ' '.join(([bin_str[::-1][i:i + chunk_n] for i in range(0, len(bin_str), chunk_n)]))[::-1]
        else:
            raise ValueError("Can't __formatNum() - unknown base")


class RegEdit(QWidget):
    def __init__(self, numBitWidth=32):
        QWidget.__init__(self)
        self.horiz_layout = QHBoxLayout(self)
        self.horiz_layout.setContentsMargins(0, 0, 0, 0)
        self.horiz_layout.setSpacing(0)
        self.nedit_val = NumEdit(numBitWidth)
        self.nedit_val.setMaximumSize(QtCore.QSize(16777215, 20))
        self.horiz_layout.addWidget(self.nedit_val)
        self.btn_read = QPushButton(self)
        self.btn_read.setText("R")
        self.btn_read.setMaximumSize(QtCore.QSize(25, 20))
        self.horiz_layout.addWidget(self.btn_read)
        self.btn_write = QPushButton(self)
        self.btn_write.setText("W")
        self.btn_write.setMaximumSize(QtCore.QSize(25, 20))
        self.horiz_layout.addWidget(self.btn_write)


class FieldEdit(QWidget):
    def __init__(self, numBitWidth=32, enumDict={}):
        QWidget.__init__(self)
        self.horiz_layout = QHBoxLayout(self)
        self.horiz_layout.setContentsMargins(0, 0, 0, 0)
        self.horiz_layout.setSpacing(6)
        if numBitWidth == 1:
            self.isSingleBitField = True
            self.chbox_val = QCheckBox(self)
            self.horiz_layout.addWidget(self.chbox_val)
        else:
            self.isSingleBitField = False
            self.nedit_val = NumEdit(numBitWidth)
            self.nedit_val.setMaximumSize(QtCore.QSize(16777215, 20))
            self.horiz_layout.addWidget(self.nedit_val)
        if enumDict:
            self.nedit_val.setMinimumSize(QtCore.QSize(100, 20))
            self.nedit_val.setMaximumSize(QtCore.QSize(100, 20))
            self.combo_enum = QComboBox(self)
            for val in enumDict.keys():
                self.combo_enum.addItem(enumDict[val])
            self.combo_enum.setMaximumSize(QtCore.QSize(16777215, 20))
            self.horiz_layout.addWidget(self.combo_enum)


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

        # Add some vars
        self.svd_file = None
        self.svd_path = None
        self.openocd_tn = OpenOCDTelnet()

    # -- Slots --
    def act_connect_triggered(self):
        if self.openocd_tn.is_opened:
            self.disconnect_openocd()
        else:
            self.connect_openocd()

    def act_open_svd_triggered(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,
                                                  "Open SVD file", "", "SVD Files (*.svd *.SVD *.xml)",
                                                  options=options)
        if fileName:
            self.read_svd(fileName)

    def act_about_triggered(self):
        text = self.about_dialog.ui.lab_version.text().replace("x.x", VERSION)
        self.about_dialog.ui.lab_version.setText(text)
        self.about_dialog.exec_()

    def act_periph_triggered(self):
        sender_name = self.sender().objectName()
        for periph in self.svd_file.device:
            if sender_name == periph["name"]:
                periph_num = self.svd_file.device.index(periph)
                periph_name = self.svd_file.device[periph_num]["name"]
                periph_descr = self.svd_file.device[periph_num]["description"]
                break

        if (self.ui.tabs_device.findChild(QWidget, periph_name)):
            self.ui.tabs_device.setCurrentWidget(self.ui.tabs_device.findChild(QWidget, periph_name))
        else:
            # create new tab
            page_periph = QWidget()
            page_periph.setObjectName(periph_name)
            # vertical layout inside
            page_periph.vert_layout = QVBoxLayout(page_periph)
            page_periph.vert_layout.setContentsMargins(6, 6, 6, 6)
            page_periph.vert_layout.setSpacing(6)
            # label with peripheral description
            page_periph.lab_periph_descr = QLabel(page_periph)
            page_periph.lab_periph_descr.setText(periph_descr)
            page_periph.lab_periph_descr.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse |
                                                                 QtCore.Qt.TextSelectableByMouse)
            page_periph.vert_layout.addWidget(page_periph.lab_periph_descr)
            # tree widget for displaying regs
            reg_col = 0
            val_col = 1
            page_periph.tree_regs = QTreeWidget(page_periph)
            page_periph.tree_regs.itemSelectionChanged.connect(self.tree_regs_selection_changed)
            page_periph.tree_regs.headerItem().setText(reg_col, "Register")
            page_periph.tree_regs.setColumnWidth(reg_col, 200)
            page_periph.tree_regs.headerItem().setText(val_col, "Value")
            for reg in self.svd_file.device[periph_num]["regs"]:
                item0 = QTreeWidgetItem(page_periph.tree_regs)
                item0.svd = reg
                item0.setText(reg_col, reg["name"])
                page_periph.reg_edit = RegEdit()
                page_periph.tree_regs.setItemWidget(item0, val_col, page_periph.reg_edit)
                page_periph.tree_regs.addTopLevelItem(item0)
                for field in reg["fields"]:
                    item1 = QTreeWidgetItem(item0)
                    item1.svd = field
                    item1.setText(reg_col, field["name"])
                    field_enum_dict = {}
                    if field["enums"]:
                        for enum in field["enums"]:
                            field_enum_dict[int(enum["value"])] = "(0x%X) %s : %s" % (int(enum["value"]), enum["name"], enum["description"])
                    page_periph.field_edit = FieldEdit(field["msb"] - field["lsb"] + 1, field_enum_dict)
                    page_periph.tree_regs.setItemWidget(item1, val_col, page_periph.field_edit)
                    item0.addChild(item1)
            page_periph.vert_layout.addWidget(page_periph.tree_regs)
            # label with register/field description
            page_periph.lab_info = QLabel(page_periph)
            page_periph.lab_info.setMaximumSize(QtCore.QSize(16777215, 40))
            page_periph.lab_info.setText("")
            page_periph.lab_info.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse |
                                                         QtCore.Qt.TextSelectableByMouse)
            page_periph.vert_layout.addWidget(page_periph.lab_info)
            # add this tab to the tab widget
            self.ui.tabs_device.addTab(page_periph, periph_name)
            self.ui.tabs_device.setCurrentIndex(self.ui.tabs_device.count() - 1)

    def tab_periph_close(self, num):
        widget = self.ui.tabs_device.widget(num)
        if widget is not None:
            widget.deleteLater()
        self.ui.tabs_device.removeTab(num)

    def tree_regs_selection_changed(self):
        tree_item = self.ui.tabs_device.currentWidget().tree_regs.selectedItems()[0]
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
        self.ui.tabs_device.currentWidget().lab_info.setText("(0x%08x)%s%s : %s\n%s" % (addr, bits, access, name, descr))

    # -- Application logic --
    def read_svd(self, path):
        try:
            self.svd_file = SVDReader(path)
            self.svd_path = path
            title = self.windowTitle()
            title = title.split(" - ")[-1]
            self.setWindowTitle(os.path.basename(path) + " - " + title)
            for periph in self.svd_file.device:
                if periph["name"] == periph["group_name"]:
                    self.ui.act_periph += [QAction(self)]
                    self.ui.act_periph[-1].setObjectName(periph["name"])
                    self.ui.act_periph[-1].setText(periph["name"])
                    self.ui.act_periph[-1].triggered.connect(self.act_periph_triggered)
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
                    self.ui.menu_periph[menu_num].act_periph[-1].triggered.connect(self.act_periph_triggered)
                    self.ui.menu_periph[menu_num].addAction(self.ui.menu_periph[menu_num].act_periph[-1])
        except:
            self.ui.statusBar.showMessage("Can't open %s - file is corrupted!" % os.path.basename(path))

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
        main_window.read_svd(sys.argv[1])
    main_window.show()
    sys.exit(app.exec_())
