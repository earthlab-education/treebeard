# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Degg\Documents\GitHub\treebeard\qgis_build\treebeard\treebeard_dialog_base.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_treebeardDialogBase(object):
    def setupUi(self, treebeardDialogBase):
        treebeardDialogBase.setObjectName("treebeardDialogBase")
        treebeardDialogBase.resize(486, 204)
        self.label = QtWidgets.QLabel(treebeardDialogBase)
        self.label.setGeometry(QtCore.QRect(10, 20, 141, 21))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(treebeardDialogBase)
        self.label_2.setGeometry(QtCore.QRect(20, 40, 131, 41))
        self.label_2.setObjectName("label_2")
        self.polygonLineEdit = QtWidgets.QLineEdit(treebeardDialogBase)
        self.polygonLineEdit.setGeometry(QtCore.QRect(170, 20, 171, 22))
        self.polygonLineEdit.setObjectName("polygonLineEdit")
        self.rasterLineEdit = QtWidgets.QLineEdit(treebeardDialogBase)
        self.rasterLineEdit.setGeometry(QtCore.QRect(170, 50, 171, 22))
        self.rasterLineEdit.setObjectName("rasterLineEdit")
        self.browsePolygonButton = QtWidgets.QPushButton(treebeardDialogBase)
        self.browsePolygonButton.setGeometry(QtCore.QRect(370, 20, 93, 28))
        self.browsePolygonButton.setObjectName("browsePolygonButton")
        self.browseRasterButton = QtWidgets.QPushButton(treebeardDialogBase)
        self.browseRasterButton.setGeometry(QtCore.QRect(370, 50, 93, 28))
        self.browseRasterButton.setObjectName("browseRasterButton")
        self.processButton = QtWidgets.QPushButton(treebeardDialogBase)
        self.processButton.setGeometry(QtCore.QRect(50, 130, 161, 28))
        self.processButton.setObjectName("processButton")
        self.lidarLineEdit = QtWidgets.QLineEdit(treebeardDialogBase)
        self.lidarLineEdit.setGeometry(QtCore.QRect(170, 80, 171, 21))
        self.lidarLineEdit.setObjectName("lidarLineEdit")
        self.label_3 = QtWidgets.QLabel(treebeardDialogBase)
        self.label_3.setGeometry(QtCore.QRect(20, 81, 121, 20))
        self.label_3.setObjectName("label_3")
        self.browseLidarButton = QtWidgets.QPushButton(treebeardDialogBase)
        self.browseLidarButton.setGeometry(QtCore.QRect(370, 80, 93, 28))
        self.browseLidarButton.setObjectName("browseLidarButton")
        self.processCanopyButton = QtWidgets.QPushButton(treebeardDialogBase)
        self.processCanopyButton.setGeometry(QtCore.QRect(250, 130, 211, 31))
        self.processCanopyButton.setObjectName("processCanopyButton")
        self.reportSpataialButton = QtWidgets.QPushButton(treebeardDialogBase)
        self.reportSpataialButton.setGeometry(QtCore.QRect(102, 170, 261, 31))
        self.reportSpataialButton.setObjectName("reportSpataialButton")

        self.retranslateUi(treebeardDialogBase)
        QtCore.QMetaObject.connectSlotsByName(treebeardDialogBase)

    def retranslateUi(self, treebeardDialogBase):
        _translate = QtCore.QCoreApplication.translate
        treebeardDialogBase.setWindowTitle(_translate("treebeardDialogBase", "Treebeard"))
        self.label.setText(_translate("treebeardDialogBase", "Select Boundary Polygon"))
        self.label_2.setText(_translate("treebeardDialogBase", "Select Raster Set"))
        self.browsePolygonButton.setText(_translate("treebeardDialogBase", "Browse"))
        self.browseRasterButton.setText(_translate("treebeardDialogBase", "Browse"))
        self.processButton.setText(_translate("treebeardDialogBase", "Process K-means"))
        self.label_3.setText(_translate("treebeardDialogBase", "Select LidAR set"))
        self.browseLidarButton.setText(_translate("treebeardDialogBase", "Browse"))
        self.processCanopyButton.setText(_translate("treebeardDialogBase", "Process Canopy Cover (Lidar)"))
        self.reportSpataialButton.setText(_translate("treebeardDialogBase", "Report Spatial Heterogeneity Sats"))