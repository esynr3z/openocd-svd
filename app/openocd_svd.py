#!/user/bin/env python3

"""
openocd-svd is a special Python utility to access peripheral registers
of ARM MCUs via OpenOCD's telnet

Run (SVD path argument is optional):
    python3 openocd_svd.py %svd_file_path%
"""

# -- Imports ------------------------------------------------------------------
import sys
import os
from svd import SVDReader
from openocd import OpenOCDTelnet
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QFileDialog
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
        fileName, _ = QFileDialog.getOpenFileName(self, "Open SVD file", "", "SVD Files (*.svd *.SVD *.xml)", options=options)
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

    # -- Functional logic --
    def read_svd(self, path):
        try:
            self.svd_file = SVDReader(path)
            self.svd_path = path
            title = self.windowTitle()
            title = title.split(" - ")[-1]
            self.setWindowTitle(os.path.basename(path) + " - " + title)
            self.ui.combo_periph.clear()
            self.ui.combo_periph.addItems([periph["name"] for periph in self.svd_file.device])
        except:
            self.ui.statusBar.showMessage("Can't open %s - file is corrupted!" % os.path.basename(path))

    def connect_openocd(self):
        try:
            self.openocd_tn.open()
            self.openocd_tn.is_opened = True
            self.ui.btn_connect.setText("Disconnect")
            self.ui.lab_status.setText("Connected to OpenOCD, target: %s" % self.openocd_tn.get_target_name())
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
