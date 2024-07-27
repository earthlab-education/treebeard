import os
import sys
import numpy as np
from qgis.PyQt.QtWidgets import QFileDialog, QDialog, QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry
from PyQt5.QtCore import QVariant, QCoreApplication
import geopandas as gpd
from shapely.geometry import shape
from scipy.ndimage import binary_opening, binary_closing
from shapely.ops import unary_union
import requests
import rioxarray
import rasterio
import whitebox

import sys
import os


from .treebeard_dialog import treebeardDialog
from .import_lidar_dialog import Ui_import_lidar_dialog as ImportLidarDialog
from .import_raster_dialog import Ui_import_raster_dialog as ImportRasterDialog

class TreebeardDialog(treebeardDialog):
    def __init__(self, parent=None):
        """Constructor for the dialog class."""
        super(TreebeardDialog, self).__init__(parent)
        self.browseRasterButton.clicked.connect(self.show_import_raster_dialog)
        self.browsePolygonButton.clicked.connect(self.browse_polygon_file)
        self.processButton.clicked.connect(self.process_files)
        self.browseLidarButton.clicked.connect(self.show_import_lidar_dialog)
        self.processCanopyButton.clicked.connect(self.process_lidar_data)
        self.raster_path = ""
        self.polygon_path = ""
        self.lidar_path = ""


    def show_import_raster_dialog(self):
        dialog = QDialog()
        ui =  ImportLidarDialog()
        ui.setupUi(dialog)
        
        ui.confirmOK.clicked.connect(lambda: self.handle_raster_selection(ui, dialog))
        ui.confirmCancel.clicked.connect(dialog.reject)

        if dialog.exec_() == QDialog.Accepted:
            self.rasterLineEdit.setText(self.raster_path)

    def show_import_lidar_dialog(self):
        dialog = QDialog()
        ui = ImportLidarDialog()
        ui.setupUi(dialog)
        
        ui.confirmOK.clicked.connect(lambda: self.handle_lidar_selection(ui, dialog))
        ui.confirmCancel.clicked.connect(dialog.reject)

        if dialog.exec_() == QDialog.Accepted:
            self.lidarLineEdit.setText(self.lidar_path)

    def handle_raster_selection(self, ui, dialog):
        selection = ui.importRasterComboBox.currentText()
        if selection == "Import from QGIS Layer":
            self.raster_path = self.import_from_qgis_layer()
        elif selection == "Import from Dataset":
            self.raster_path = self.download_from_dataset()
        elif selection == "Import from Desktop":
            self.raster_path, _ = QFileDialog.getOpenFileName(dialog, "Select Raster File", "", "Raster files (*.tif)")
        dialog.accept()

    def handle_lidar_selection(self, ui, dialog):
        selection = ui.importLidarComboBox.currentText()
        if selection == "Import from QGIS Layer":
            self.lidar_path = self.import_from_qgis_layer()
        elif selection == "Import from Dataset":
            self.lidar_path = self.download_from_dataset()
        elif selection == "Import from Desktop":
            self.lidar_path, _ = QFileDialog.getOpenFileName(dialog, "Select LiDAR File", "", "LiDAR files (*.las)")
        dialog.accept()
    
    def download_lidar_files(self, tiles_by_area, lidar_las_dir):
        las_root_url = 'https://lidararchive.s3.amazonaws.com/2020_CSPN_Q2/'
        canopy_dict = {}
        
        if not self.boundary_polygon_path:
            QMessageBox.critical(None, "Error", "Please import a boundary polygon first.")
            return

        proj_area_gdf = gpd.read_file(self.boundary_polygon_path)
        site_to_process = tiles_by_area[tiles_by_area['Proj_ID'] == 'Zumwinkel'].copy()
        for index, row in site_to_process.iterrows():
            tiles = row['tile']
            proj_area_name = row['Proj_ID']
            sel_proj_area_gdf = proj_area_gdf[proj_area_gdf['Proj_ID'] == proj_area_name]
            tile_agg = []
            print("Processing LIDAR for " + proj_area_name)
            for tile in tiles:
                file_name = tile + ".las"
                print("Processing LIDAR tile " + tile)
                tile_path = os.path.join(lidar_las_dir, file_name)
                download_url = las_root_url + tile + ".las"
                if not os.path.exists(tile_path):
                    response = requests.get(download_url)
                    if response.status_code == 200:
                        with open(tile_path, 'wb') as file:
                            file.write(response.content)
                        print(f"File downloaded successfully and saved to {tile_path}")
                    else:
                        print(f"Failed to download file. Status code: {response.status_code}")

    def browse_polygon_file(self):
        """Browse and select a boundary polygon file."""
        self.polygon_path, _ = QFileDialog.getOpenFileName(self, "Select Boundary Polygon File", "", "Vector files (*.shp *.geojson)")
        if self.polygon_path:
            self.polygonLineEdit.setText(self.polygon_path)

    def process_files(self):
        """Process the selected files."""
        if not self.raster_path or not self.polygon_path:
            QMessageBox.critical(self, "Error", "Please select both raster and polygon files.")
            return
        # Add processing logic here

    def load_from_qgis_layer(self):
        pass

    def download_from_dataset(self):
        pass

    def load_from_pc(self):
        self.lidar_path, _ = QFileDialog.getOpenFileName(self, "Select LiDAR File", "", "LAS files (*.las *.laz)")
        if self.lidar_path:
            self.lidarLineEdit.setText(self.lidar_path)

    def process_lidar_data(self):
        lidar_file = self.lidarLineEdit.text()
        if not lidar_file:
            QMessageBox.critical(self, "Error", "Please select a LiDAR file.")
            return

        try:
            output_tif = os.path.join(os.path.dirname(lidar_file), 'processed_lidar.tif')
            self.convert_las_to_tif(lidar_file, output_tif, 'first')
            lidar_cleaned = self.clean_raster_rioxarray(rioxarray.open_rasterio(output_tif))
            canopy_gdf = self.export_lidar_canopy_tif(lidar_cleaned, output_tif)
            
            # Add the processed LiDAR data to QGIS as a raster layer
            self.load_raster_to_qgis(output_tif, 'Processed LiDAR Canopy')

            QMessageBox.information(self, "Success", "LiDAR processing complete.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))(e)

    def convert_las_to_tif(self, input_las, output_tif, return_type):
        wbt = whitebox.WhiteboxTools()
        if return_type == "first":
            wbt.lidar_idw_interpolation(
                i=input_las,
                output=output_tif,
                parameter="elevation",
                returns="first",
                resolution=1.0,
                radius=3.0
            )
        elif return_type == "ground":
            wbt.lidar_idw_interpolation(
                i=input_las,
                output=output_tif,
                parameter="elevation",
                returns="ground",
                resolution=1.0,
                radius=3.0
            )
        else:
            raise ValueError("Invalid return_type. Use 'first' or 'ground'.")

    def clean_raster_rioxarray(self, raster_xarray, operation='opening', structure_size=3):
        raster_data = raster_xarray.values
        if raster_data.ndim == 3 and raster_data.shape[0] == 1:
            raster_data = raster_data[0, :, :]
        binary_raster = raster_data == 1
        structure = np.ones((structure_size, structure_size), dtype=int)
        if operation == 'opening':
            cleaned_raster = binary_opening(binary_raster, structure=structure)
        elif operation == 'closing':
            cleaned_raster = binary_closing(binary_raster, structure=structure)
        else:
            raise ValueError("Operation must be 'opening' or 'closing'")
        raster_data_cleaned = np.where(cleaned_raster, 1, 0)
        if raster_xarray.values.ndim == 3:
            raster_data_cleaned = np.expand_dims(raster_data_cleaned, axis=0)
        cleaned_raster_xarray = raster_xarray.copy(data=raster_data_cleaned)
        return cleaned_raster_xarray

    def export_lidar_canopy_tif(self, lidar_cleaned, output_path):
        lidar_cleaned = lidar_cleaned.where(lidar_cleaned != 1.7976931348623157e+308, np.nan)
        lidar_cleaned.rio.to_raster(output_path, overwrite=True)
        binary_mask = lidar_cleaned.squeeze()
        mask = binary_mask == 1
        transform = binary_mask.rio.transform()
        shapes = rasterio.features.shapes(mask.astype(np.int16).values, transform=transform)
        polygons = [shape(geom) for geom, value in shapes if value == 1]
        canopy_gdf = gpd.GeoDataFrame({'geometry': polygons})
        return canopy_gdf

    def browse_raster_file(self):
        self.raster_path, _ = QFileDialog.getOpenFileName(self, "Select Raster File", "", "Raster files (*.tif)")
        if self.raster_path:
            self.rasterLineEdit.setText(self.raster_path)

    def browse_polygon_file(self):
        self.polygon_path, _ = QFileDialog.getOpenFileName(self, "Select Boundary Polygon File", "", "Vector files (*.shp *.geojson)")
        if self.polygon_path:
            self.polygonLineEdit.setText(self.polygon_path)

    def load_polygons_to_qgis(self, gdf, layer_name='Clustered Polygons'):
        vl = QgsVectorLayer("Polygon?crs=EPSG:4326", layer_name, "memory")
        pr = vl.dataProvider()
        pr.addAttributes([QgsField("cluster", QVariant.Int)])
        vl.updateFields()
        for _, row in gdf.iterrows():
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromWkt(row['geometry'].wkt))
            feat.setAttributes([int(row['cluster'])])
            pr.addFeatures([feat])
        QgsProject.instance().addMapLayer(vl)
        print(f"Layer '{layer_name}' added to QGIS.")

    def calculate_spatial_statistics(self, gdf):
        stats = gdf['geometry'].area.describe()
        print("Spatial Statistics:")
        print(stats)

class Treebeard:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = self.tr(u'&Treebeard')
        self.first_start = None

    def tr(self, message):
        return QCoreApplication.translate('Treebeard', message)

    def initGui(self):
        icon_path = ':/plugins/treebeard/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Treebeard'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )

    def add_action(self, icon_path, text, callback, enabled_flag=True, add_to_menu=True, add_to_toolbar=True, status_tip=None, whats_this=None, parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        if status_tip:
            action.setStatusTip(status_tip)
        if whats_this:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.iface.addToolBarIcon(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&Treebeard'), action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        dialog = TreebeardDialog()
        dialog.exec_()
