# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Degg\Documents\GitHub\treebeard\qgis_build\treebeard\import_raster_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_import_raster_dialog(object):
    def setupUi(self, import_raster_dialog):
        import_raster_dialog.setObjectName("import_raster_dialog")
        import_raster_dialog.resize(378, 102)
        self.importRasterComboBox = QtWidgets.QComboBox(import_raster_dialog)
        self.importRasterComboBox.setGeometry(QtCore.QRect(10, 20, 191, 22))
        self.importRasterComboBox.setObjectName("importRasterComboBox")
        self.importRasterComboBox.addItem("")
        self.importRasterComboBox.addItem("")
        self.importRasterComboBox.addItem("")
        self.confirmOK = QtWidgets.QPushButton(import_raster_dialog)
        self.confirmOK.setGeometry(QtCore.QRect(240, 20, 93, 28))
        self.confirmOK.setObjectName("confirmOK")
        self.confirmCancel = QtWidgets.QPushButton(import_raster_dialog)
        self.confirmCancel.setGeometry(QtCore.QRect(240, 60, 93, 28))
        self.confirmCancel.setObjectName("confirmCancel")

        self.retranslateUi(import_raster_dialog)
        QtCore.QMetaObject.connectSlotsByName(import_raster_dialog)

    def retranslateUi(self, import_raster_dialog):
        _translate = QtCore.QCoreApplication.translate
        import_raster_dialog.setWindowTitle(_translate("import_raster_dialog", "Dialog"))
        self.importRasterComboBox.setItemText(0, _translate("import_raster_dialog", "Import from QGIS Layer"))
        self.importRasterComboBox.setItemText(1, _translate("import_raster_dialog", "Import from Dataset"))
        self.importRasterComboBox.setItemText(2, _translate("import_raster_dialog", "Import from Desktop"))
        self.confirmOK.setText(_translate("import_raster_dialog", "OK"))
        self.confirmCancel.setText(_translate("import_raster_dialog", "Cancel"))
