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
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QWidget, QFileDialog, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QLineEdit, QAction, QMenu
from ui_main import Ui_MainWindow
from ui_about import Ui_Dialog


# -- Global variables ---------------------------------------------------------
VERSION = "0.1"


# -- Custom widgets -----------------------------------------------------------
class MyLineEdit(QLineEdit):
    def __init__(self):
        QLineEdit.__init__(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__contextMenu)
        self.textMode = 10
        self.textBitWidth = 32

    def __contextMenu(self, pos):
        self.menu = self.createStandardContextMenu()

        self.menu.act_to_dec = QAction(self)
        self.menu.act_to_dec.setText("Convert to Dec")
        self.menu.act_to_dec.triggered.connect(self.setFormatDec)
        self.menu.act_to_hex = QAction(self)
        self.menu.act_to_hex.setText("Convert to Hex")
        self.menu.act_to_hex.triggered.connect(self.setFormatHex)
        self.menu.act_to_bin = QAction(self)
        self.menu.act_to_bin.setText("Convert to Bin")
        self.menu.act_to_bin.triggered.connect(self.setFormatBin)
        self.menu.insertActions(self.menu.actions()[0],
                                [self.menu.act_to_dec, self.menu.act_to_hex, self.menu.act_to_bin])
        self.menu.insertSeparator(self.menu.actions()[3])

        self.menu.exec_(QCursor.pos())

    def setValidatorDec(self):
        print("Change validator to Dec")

    def setValidatorHex(self):
        print("Change validator to Hex")

    def setValidatorBin(self):
        print("Change validator to Bin")

    def setFormatDec(self):
        print("Convert to Dec")
        self.setText(str(int(self.text().replace(" ", ""), self.textMode)))
        self.textMode = 10
        self.setValidatorDec()

    def setFormatHex(self):
        print("Convert to Hex")
        self.setText(format(int(self.text().replace(" ", ""), self.textMode),
                            '#0%dx' % (2 + int(self.textBitWidth / 4) + (self.textBitWidth % 4 > 0))))
        self.textMode = 16
        self.setValidatorHex()

    def setFormatBin(self):
        print("Convert to Bin")
        chunk_n = 4
        bin_str = format(int(self.text(), self.textMode), '0%db' % self.textBitWidth)
        spaced_bin_str = ' '.join(list(reversed([bin_str[::-1][i:i + chunk_n] for i in range(0, len(bin_str), chunk_n)])))
        self.setText(spaced_bin_str)
        self.textMode = 2
        self.setValidatorBin()


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
        print("Connect triggered")
        if self.openocd_tn.is_opened:
            self.disconnect_openocd()
        else:
            self.connect_openocd()

    def act_open_svd_triggered(self):
        print("Open SVD action triggered")
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,
                                                  "Open SVD file", "", "SVD Files (*.svd *.SVD *.xml)",
                                                  options=options)
        if fileName:
            print(self.svd_path)
            self.read_svd(fileName)

    def act_about_triggered(self):
        print("About action triggered")
        text = self.about_dialog.ui.lab_version.text().replace("x.x", VERSION)
        self.about_dialog.ui.lab_version.setText(text)
        self.about_dialog.exec_()

    def act_periph_triggered(self):
        print("Action periph triggered")
        sender_name = self.sender().objectName()
        for periph in self.svd_file.device:
            if sender_name == periph["name"]:
                periph_num = self.svd_file.device.index(periph)
                periph_name = self.svd_file.device[periph_num]["name"]
                periph_descr = self.svd_file.device[periph_num]["description"]
                break

        if (self.ui.tab_periph.findChild(QWidget, periph_name)):
            self.ui.tab_periph.setCurrentWidget(self.ui.tab_periph.findChild(QWidget, periph_name))
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
                ledit_reg = MyLineEdit()
                ledit_reg.setText("0")
                ledit_reg.textBitWidth = 32
                ledit_reg.setFormatHex()
                ledit_reg.setMaximumSize(QtCore.QSize(16777215, 20))
                page_periph.tree_regs.setItemWidget(item0, val_col, ledit_reg)
                page_periph.tree_regs.addTopLevelItem(item0)
                for field in reg["fields"]:
                    item1 = QTreeWidgetItem(item0)
                    item1.svd = field
                    item1.setText(reg_col, field["name"])
                    ledit_field = MyLineEdit()
                    ledit_field.setText("0")
                    ledit_field.textBitWidth = field["msb"] - field["lsb"] + 1
                    ledit_field.setFormatHex()
                    ledit_field.setMaximumSize(QtCore.QSize(16777215, 20))
                    page_periph.tree_regs.setItemWidget(item1, val_col, ledit_field)
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
            self.ui.tab_periph.addTab(page_periph, periph_name)
            self.ui.tab_periph.setCurrentIndex(self.ui.tab_periph.count() - 1)

    def tab_periph_close(self, num):
        print("Tab periph closed: %d" % num)
        widget = self.ui.tab_periph.widget(num)
        if widget is not None:
            widget.deleteLater()
        self.ui.tab_periph.removeTab(num)

    def tree_regs_selection_changed(self):
        print("Tree regs selection changed")
        tree_item = self.ui.tab_periph.currentWidget().tree_regs.selectedItems()[0]
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
        self.ui.tab_periph.currentWidget().lab_info.setText("(0x%08x)%s%s : %s\n%s" % (addr, bits, access, name, descr))

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
