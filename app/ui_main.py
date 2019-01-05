# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'main.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowModality(QtCore.Qt.ApplicationModal)
        MainWindow.setEnabled(True)
        MainWindow.resize(768, 768)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        MainWindow.setDocumentMode(False)
        MainWindow.setTabShape(QtWidgets.QTabWidget.Rounded)
        MainWindow.setUnifiedTitleAndToolBarOnMac(False)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setContentsMargins(6, 6, 6, -1)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tabs_device = QtWidgets.QTabWidget(self.centralwidget)
        self.tabs_device.setTabPosition(QtWidgets.QTabWidget.South)
        self.tabs_device.setTabsClosable(True)
        self.tabs_device.setMovable(True)
        self.tabs_device.setObjectName("tabs_device")
        self.verticalLayout.addWidget(self.tabs_device)
        self.verticalLayout_3.addLayout(self.verticalLayout)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 768, 28))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuHelp = QtWidgets.QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        self.menuView = QtWidgets.QMenu(self.menubar)
        self.menuView.setObjectName("menuView")
        MainWindow.setMenuBar(self.menubar)
        self.statusBar = QtWidgets.QStatusBar(MainWindow)
        self.statusBar.setObjectName("statusBar")
        MainWindow.setStatusBar(self.statusBar)
        self.act_quit = QtWidgets.QAction(MainWindow)
        self.act_quit.setObjectName("act_quit")
        self.act_open_svd = QtWidgets.QAction(MainWindow)
        self.act_open_svd.setObjectName("act_open_svd")
        self.act_about = QtWidgets.QAction(MainWindow)
        self.act_about.setObjectName("act_about")
        self.act_connect = QtWidgets.QAction(MainWindow)
        self.act_connect.setObjectName("act_connect")
        self.act_open_packed_svd = QtWidgets.QAction(MainWindow)
        self.act_open_packed_svd.setObjectName("act_open_packed_svd")
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.act_open_svd)
        self.menuFile.addAction(self.act_open_packed_svd)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.act_connect)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.act_quit)
        self.menuHelp.addAction(self.act_about)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuView.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(MainWindow)
        self.tabs_device.setCurrentIndex(-1)
        self.act_quit.triggered.connect(MainWindow.close)
        self.act_open_svd.triggered.connect(MainWindow.handle_act_open_svd_triggered)
        self.act_about.triggered.connect(MainWindow.handle_act_about_triggered)
        self.tabs_device.tabCloseRequested['int'].connect(MainWindow.handle_tab_periph_close)
        self.act_connect.triggered.connect(MainWindow.handle_act_connect_triggered)
        self.act_open_packed_svd.triggered.connect(MainWindow.handle_act_open_packed_svd_triggered)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "openocd-svd"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuHelp.setTitle(_translate("MainWindow", "Help"))
        self.menuView.setTitle(_translate("MainWindow", "View"))
        self.act_quit.setText(_translate("MainWindow", "Quit"))
        self.act_quit.setStatusTip(_translate("MainWindow", "Quit the utility"))
        self.act_quit.setShortcut(_translate("MainWindow", "Ctrl+Q"))
        self.act_open_svd.setText(_translate("MainWindow", "Open SVD from path"))
        self.act_open_svd.setStatusTip(_translate("MainWindow", "Open SVD file"))
        self.act_open_svd.setShortcut(_translate("MainWindow", "Ctrl+O"))
        self.act_about.setText(_translate("MainWindow", "About"))
        self.act_about.setStatusTip(_translate("MainWindow", "Show information about utility"))
        self.act_connect.setText(_translate("MainWindow", "Connect OpenOCD"))
        self.act_connect.setStatusTip(_translate("MainWindow", "Open/close connection to OpenOCD"))
        self.act_connect.setShortcut(_translate("MainWindow", "Ctrl+E"))
        self.act_open_packed_svd.setText(_translate("MainWindow", "Open SVD from packed"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

