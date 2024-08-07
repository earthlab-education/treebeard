import os
import sys

import geopandas as gpd
import numpy as np
from qgis.PyQt.QtWidgets import QFileDialog, QDialog, QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry
from PyQt5.QtCore import QVariant, QCoreApplication
import requests
import rioxarray
import rasterio
from shapely.geometry import shape
from scipy.ndimage import binary_opening, binary_closing
from shapely.ops import unary_union

import whitebox

import sys
import os


from .treebeard_dialog_base import treebeardDialog
from .import_lidar_dialog import Ui_import_lidar_dialog as ImportLidarDialog
from .import_raster_dialog import Ui_import_raster_dialog as ImportRasterDialog
from .process_lidar import  process_canopy_areas, process_lidar_to_canopy

COLO_CRS = "EPSG:6430"

# def ensure_crs(geodf, target_crs=COLO_CRS):
#     """Ensure the GeoDataFrame is in the specified CRS."""
#     if geodf.crs =  None:
#         geodf = geodf.rio.write_crs(target_crs)

#     elif geodf.crs != target_crs:
#         geodf = geodf.to_crs(target_crs)
#     return geodf

# def ensure_raster_crs(raster, target_crs=COLO_CRS):
#     """Ensure the raster is in the specified CRS."""
#     if raster.rio.crs != target_crs:
#         raster = raster.rio.reproject(target_crs)
#     return raster

def convert_boundary_to_gdf(boundary_path, crs):
    """Load in boundary file to make sure it is in gdf format before processing """


class TreebeardDialog(treebeardDialog):
    def __init__(self, parent=None):
        """Constructor for the dialog class."""
        super(TreebeardDialog, self).__init__(parent)
        self.browseRasterButton.clicked.connect(self.show_import_raster_dialog)
        self.browsePolygonButton.clicked.connect(self.browse_polygon_file)
        self.processButton.clicked.connect(self.process_kmeans)
        self.browseLidarButton.clicked.connect(self.show_import_lidar_dialog)
        self.processCanopyButton.clicked.connect(self.process_lidar_data)
        self.defineProjectDir.clicked.connect(self.set_proj_dir)
        self.raster_path = ""
        self.polygon_path = ""
        self.lidar_path = ""
        self.output_dir = ""

    def set_proj_dir(self):
        """Sets folder for output files"""
        directory = QFileDialog.getExistingDiretory(self, "Select Output Directory")

        if directory:
            self.output_dir = directory
            self.outputLineEdit.setText(self.output_dir)

    
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
        # elif selection == "Import from Dataset":
        #     self.raster_path = self.download_from_dataset()
        elif selection == "Import from Desktop":
            self.raster_path, _ = QFileDialog.getOpenFileName(dialog, "Select Raster File", "", "Raster files (*.tif)")
        dialog.accept()

    def handle_lidar_selection(self, ui, dialog):
        selection = ui.importLidarComboBox.currentText()
        if selection == "Import from QGIS Layer":
            self.lidar_path = self.import_from_qgis_layer()
        # elif selection == "Import from Dataset":
        #     self.lidar_path = self.download_from_dataset()
        elif selection == "Import from Desktop":
            self.lidar_path, _ = QFileDialog.getOpenFileName(dialog, "Select LiDAR File", "", "LiDAR files (*.las)")
        dialog.accept()
    
    # def download_lidar_files(self, tiles_by_area, lidar_las_dir):
    #     las_root_url = 'https://lidararchive.s3.amazonaws.com/2020_CSPN_Q2/'
    #     canopy_dict = {}
        
    #     if not self.boundary_polygon_path:
    #         QMessageBox.critical(None, "Error", "Please import a boundary polygon first.")
    #         return

    #     proj_area_gdf = gpd.read_file(self.boundary_polygon_path)
    #     site_to_process = tiles_by_area[tiles_by_area['Proj_ID'] == 'Zumwinkel'].copy()
    #     for index, row in site_to_process.iterrows():
    #         tiles = row['tile']
    #         proj_area_name = row['Proj_ID']
    #         sel_proj_area_gdf = proj_area_gdf[proj_area_gdf['Proj_ID'] == proj_area_name]
    #         tile_agg = []
    #         print("Processing LIDAR for " + proj_area_name)
    #         for tile in tiles:
    #             file_name = tile + ".las"
    #             print("Processing LIDAR tile " + tile)
    #             tile_path = os.path.join(lidar_las_dir, file_name)
    #             download_url = las_root_url + tile + ".las"
    #             if not os.path.exists(tile_path):
    #                 response = requests.get(download_url)
    #                 if response.status_code == 200:
    #                     with open(tile_path, 'wb') as file:
    #                         file.write(response.content)
    #                     print(f"File downloaded successfully and saved to {tile_path}")
    #                 else:
    #                     print(f"Failed to download file. Status code: {response.status_code}")

    def browse_polygon_file(self):
        """Browse and select a boundary polygon file."""
        self.polygon_path, _ = QFileDialog.getOpenFileName(self, "Select Boundary Polygon File", "", "Vector files (*.shp *.geojson)")
        if self.polygon_path:
            self.polygonLineEdit.setText(self.polygon_path)

    # def process_files(self):
    #     """Process the selected files."""
    #     if not self.raster_path or not self.polygon_path:
    #         QMessageBox.critical(self, "Error", "Please select both raster and polygon files.")
    #         return
    #     # Add processing logic here


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
            # code from for_chris 
            canopy_gdf = process_lidar_to_canopy(proj_area, las_folder_path, canopy_height=5)

            # Specify the output path from QGIS parameter? Or default to the earth analytics folder
            output_path = os.path.join(lidar_las_dir, "output")

            if not os.path.exists(output_path):
                os.makedirs(output_path)

            process_canopy_areas(canopy_gdf, proj_area, output_path, buffer_distance=5)


            # output_tif = os.path.join(os.path.dirname(lidar_file), 'processed_lidar.tif')
            # convert_las_to_tif(lidar_file, output_tif, 'first')
            # lidar_cleaned = clean_raster_rioxarray(rioxarray.open_rasterio(output_tif))
            # canopy_gdf = export_lidar_canopy_tif(lidar_cleaned, output_tif)
 
            #  # Ensure CRS for both raster and vector data
            # canopy_gdf = ensure_crs(canopy_gdf)
            # study_area = gpd.read_file(self.polygonLineEdit.text())
            # study_area = ensure_crs(study_area)

            # # Further processing
            # clipped_buffer, exploded_gap_gdf = process_canopy_areas(canopy_gdf, study_area)

            # # Load raster to QGIS
            # self.load_raster_to_qgis(output_tif, 'Processed LiDAR Canopy')
            QMessageBox.information(self, "Success", "LiDAR processing complete.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def load_raster_to_qgis(self, raster_path, layer_name):
        raster_layer = QgsRasterLayer(raster_path, layer_name)
        if not raster_layer.isValid():
            raise IOError(f"Failed to load raster layer: {raster_path}")
        QgsProject.instance().addMapLayer(raster_layer)

    def browse_raster_file(self):
        self.raster_path, _ = QFileDialog.getOpenFileName(self, "Select Raster File", "", "Raster files (*.tif)")
        if self.raster_path:
            self.rasterLineEdit.setText(self.raster_path)
    
    def load_raster_to_qgis(self, raster_path, layer_name='Loaded Raster'):
        """
        Load a raster file into QGIS.
        :param raster_path: Path to the raster file.
        :param layer_name: Name of the QGIS layer.
        """
         # Check if the raster file exists
        if not os.path.exists(raster_path):
            QMessageBox.critical(self, "Error", f"Raster file {raster_path} does not exist.")
            return
        
        # Load the raster layer
        raster_layer = QgsRasterLayer(raster_path, layer_name)
        
        # Check if the raster layer is valid
        if not raster_layer.isValid():
            QMessageBox.critical(self, "Error", f"Failed to load raster layer from {raster_path}.")
            return
        
        # Add the raster layer to the QGIS project
        QgsProject.instance().addMapLayer(raster_layer)
        QMessageBox.information(self, "Success", f"Raster layer '{layer_name}' loaded successfully.")


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
    
    def process_kmeans(self, boundary_gdf, aoi_raster):
        """Run kmeans processing from segment_drapp"""

    pass    
    
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
