# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'svd.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_SVDDialog(object):
    def setupUi(self, SVDDialog):
        SVDDialog.setObjectName("SVDDialog")
        SVDDialog.resize(400, 500)
        self.verticalLayout = QtWidgets.QVBoxLayout(SVDDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tree_svd = QtWidgets.QTreeWidget(SVDDialog)
        self.tree_svd.setObjectName("tree_svd")
        self.tree_svd.headerItem().setText(0, "1")
        self.verticalLayout.addWidget(self.tree_svd)
        self.btn_dialog = QtWidgets.QDialogButtonBox(SVDDialog)
        self.btn_dialog.setOrientation(QtCore.Qt.Horizontal)
        self.btn_dialog.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.btn_dialog.setObjectName("btn_dialog")
        self.verticalLayout.addWidget(self.btn_dialog)

        self.retranslateUi(SVDDialog)
        self.btn_dialog.accepted.connect(SVDDialog.accept)
        self.btn_dialog.rejected.connect(SVDDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(SVDDialog)

    def retranslateUi(self, SVDDialog):
        _translate = QtCore.QCoreApplication.translate
        SVDDialog.setWindowTitle(_translate("SVDDialog", "Select SVD"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    SVDDialog = QtWidgets.QDialog()
    ui = Ui_SVDDialog()
    ui.setupUi(SVDDialog)
    SVDDialog.show()
    sys.exit(app.exec_())

