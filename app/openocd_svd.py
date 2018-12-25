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
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QWidget, QFileDialog, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QLineEdit
from ui_main import Ui_MainWindow
from ui_about import Ui_Dialog


# -- Global variables ---------------------------------------------------------
VERSION = "0.1"


# -- Main window --------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        # Set up the user interface from QtDesigner
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Modify UI
        self.about_dialog = QDialog(self)
        self.about_dialog.ui = Ui_Dialog()
        self.about_dialog.ui.setupUi(self.about_dialog)

        # Add some vars
        self.svd_file = None
        self.svd_path = None
        self.openocd_tn = OpenOCDTelnet()

    # -- Slots --
    def btn_connect_clicked(self):
        print("Connect button clicked")
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

    def act_autoread_triggered(self, checkbox):
        print("Auto read action triggered: %d" % int(checkbox))
        self.opt_autoread = checkbox

    def act_about_triggered(self):
        print("About action triggered")
        text = self.about_dialog.ui.lab_version.text().replace("x.x", VERSION)
        self.about_dialog.ui.lab_version.setText(text)
        self.about_dialog.exec_()

    def act_autowrite_triggered(self, checkbox):
        print("Auto write action triggered: %d" % int(checkbox))
        self.opt_autowrite = checkbox

    def combo_periph_changed(self, num):
        print("Periph combobox changed: %d" % num)
        periph_name = self.svd_file.device[num - 1]["name"]
        periph_descr = self.svd_file.device[num - 1]["description"]
        if num > 0:
            if (self.ui.tab_periph.findChild(QWidget, periph_name)):
                self.ui.tab_periph.setCurrentWidget(self.ui.tab_periph.findChild(QWidget, periph_name))
            else:
                # create new tab
                periph_page = QWidget()
                periph_page.setObjectName(periph_name)
                # vertical layout inside
                periph_page.vert_layout = QVBoxLayout(periph_page)
                periph_page.vert_layout.setContentsMargins(6, 6, 6, 6)
                periph_page.vert_layout.setSpacing(6)
                # label with peripheral description
                periph_page.lab_periph_descr = QLabel(periph_page)
                periph_page.lab_periph_descr.setText(periph_descr)
                periph_page.lab_periph_descr.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse |
                                                                     QtCore.Qt.TextSelectableByMouse)
                periph_page.vert_layout.addWidget(periph_page.lab_periph_descr)
                # tree widget for displaying regs
                reg_col = 0
                val_col = 1
                periph_page.tree_regs = QTreeWidget(periph_page)
                periph_page.tree_regs.itemSelectionChanged.connect(self.tree_regs_selection_changed)
                # periph_page.tree_regs.setObjectName("tree_regs")
                periph_page.tree_regs.headerItem().setText(reg_col, "Register")
                periph_page.tree_regs.setColumnWidth(reg_col, 200)
                periph_page.tree_regs.headerItem().setText(val_col, "Value")
                for reg in self.svd_file.device[num - 1]["regs"]:
                    item0 = QTreeWidgetItem(periph_page.tree_regs)
                    item0.svd = reg
                    item0.setText(reg_col, reg["name"])
                    reg_line_edit = QLineEdit()
                    reg_line_edit.setMaximumSize(QtCore.QSize(16777215, 20))
                    reg_line_edit.setText("0x00000000")
                    periph_page.tree_regs.setItemWidget(item0, val_col, reg_line_edit)
                    periph_page.tree_regs.addTopLevelItem(item0)
                    for field in reg["fields"]:
                        item1 = QTreeWidgetItem(item0)
                        item1.svd = field
                        item1.setText(reg_col, field["name"])
                        field_line_edit = QLineEdit()
                        field_line_edit.setMaximumSize(QtCore.QSize(16777215, 20))
                        field_line_edit.setText("0")
                        periph_page.tree_regs.setItemWidget(item1, val_col, field_line_edit)
                        item0.addChild(item1)
                periph_page.vert_layout.addWidget(periph_page.tree_regs)
                # label with register/field description
                periph_page.lab_info = QLabel(periph_page)
                periph_page.lab_info.setMaximumSize(QtCore.QSize(16777215, 40))
                periph_page.lab_info.setText("")
                periph_page.lab_info.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse |
                                                             QtCore.Qt.TextSelectableByMouse)
                periph_page.vert_layout.addWidget(periph_page.lab_info)
                # add this tab to the tab widget
                self.ui.tab_periph.addTab(periph_page, periph_name)
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
        if "access" in tree_item.svd.keys():
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
            self.ui.combo_periph.clear()
            self.ui.combo_periph.addItems(["---"])
            self.ui.combo_periph.addItems([periph["name"] for periph in self.svd_file.device])
        except:
            self.ui.statusBar.showMessage("Can't open %s - file is corrupted!" % os.path.basename(path))

    def connect_openocd(self):
        try:
            self.openocd_tn.open()
            self.openocd_tn.is_opened = True
            self.ui.btn_connect.setText("Disconnect")
            self.ui.lab_status.setText("Connected, target: %s" % self.openocd_tn.get_target_name())
        except:
            self.ui.statusBar.showMessage("Can't connect to OpenOCD!")

    def disconnect_openocd(self):
        self.openocd_tn.close()
        self.openocd_tn.is_opened = False
        self.ui.btn_connect.setText("Connect")
        self.ui.lab_status.setText("Not connected to OpenOCD")


# -- Standalone run -----------------------------------------------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    if len(sys.argv) > 1:
        main_window.read_svd(sys.argv[1])
    main_window.show()
    sys.exit(app.exec_())
