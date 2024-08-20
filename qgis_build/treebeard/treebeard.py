import os
import logging
import subprocess
import sys
import traceback

import geopandas as gpd
import numpy as np
from qgis.PyQt.QtWidgets import QApplication, QFileDialog, QDialog, QAction, QMessageBox, QInputDialog
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry
from PyQt5.QtCore import Qt, QVariant, QCoreApplication
import requests
import rioxarray
import rasterio
from shapely.geometry import shape
from scipy.ndimage import binary_opening, binary_closing
from shapely.ops import unary_union

import whitebox


from .treebeard_dialog import treebeardDialog
from .import_lidar_dialog import Ui_import_lidar_dialog as ImportLidarDialog
from .import_raster_dialog import Ui_import_raster_dialog as ImportRasterDialog
from .progress_dialog import Ui_Dialog as ProgressDialog
from .process_lidar import  process_canopy_areas, process_lidar_to_canopy

# COLO_CRS = "EPSG:6430"

# Set up logging
logger = logging.getLogger('qgis_plugin')
logger.setLevel(logging.DEBUG)  # Set to the lowest level to capture all logs

# Create console handler and set level to debug
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add formatter to console handler
console_handler.setFormatter(formatter)

# Add console handler to logger
logger.addHandler(console_handler)

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


class TreebeardDialog(treebeardDialog):
    def __init__(self, parent=None):
        """Constructor for the dialog class."""
        super(TreebeardDialog, self).__init__(parent)
        self.browseRasterButton.clicked.connect(self.show_import_raster_dialog)
        self.browsePolygonButton.clicked.connect(self.browse_polygon_file)
        self.processButton.clicked.connect(self.process_kmeans)
        self.browseLidarButton.clicked.connect(self.show_import_lidar_dialog)
        self.processCanopyButton.clicked.connect(self.process_lidar_data)
        self.browseOutputButton.clicked.connect(self.set_proj_dir)
        self.raster_path = ""
        self.proj_area_poly = ""
        self.lidar_path = ""
        self.output_dir = ""

    def set_proj_dir(self):
        """Sets folder for output files"""
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")

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
        
        elif selection == "Import from Desktop":
            # Prompt user to select a LiDAR file
            lidar_path = QFileDialog.getExistingDirectory(dialog, "Select LiDAR Directory")
            
            # Check if the user selected a file
            if not lidar_path:
                QMessageBox.critical(dialog, "Error", "No LiDAR file selected.")
                return

            # Normalize the file path
            lidar_path = os.path.normpath(lidar_path)
            
            # Ensure the directory and file are valid
            if not os.path.exists(lidar_path):
                QMessageBox.critical(dialog, "Error", f"The file does not exist: {lidar_path}")
                return

            # Store the valid file path
            self.lidar_path = lidar_path
        
        # Close the dialog if a valid file was selected
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
        # Open file dialog to select the boundary polygon file
        proj_area_path, _ = QFileDialog.getOpenFileName(self, "Select Boundary Polygon File", "", "Vector files (*.shp *.geojson)")
        
        if proj_area_path:
            # Update the class variable with the selected file path
            self.proj_area_poly = proj_area_path
            
            # Update the UI element with the selected file path
            self.polygonLineEdit.setText(self.proj_area_poly)
            
        
    def set_proj_area_gdf(self, boundary_path):
        try:
            if not boundary_path:
                raise ValueError("No boundary file set. Please select a boundary file.")

            if not os.path.exists(boundary_path):
                raise FileNotFoundError(f"The boundary file does not exist: {boundary_path}")

            proj_area_gdf = gpd.read_file(boundary_path)
            if proj_area_gdf.empty:
                raise ValueError("The boundary file was loaded but contains no data.")

            if proj_area_gdf.crs is None:
                raise AttributeError("Boundary file has no crs attribute.")

            logger.debug(f"Boundary file loaded and CRS set to {proj_area_gdf.crs}")
            return proj_area_gdf
        except Exception as e:
            logger.error("Failed to load and set CRS for the boundary file.", exc_info=True)
            raise



    def load_from_pc(self):
        self.lidar_path, _ = QFileDialog.getOpenFileName(self, "Select LiDAR File", "", "LAS files (*.las *.laz)")
        if self.lidar_path:
            self.lidarLineEdit.setText(self.lidar_path)

    def process_lidar_data(self):
        logger.info("Clicked on 'Process Canopy' button. Starting process_lidar_data...")

        lidar_file = self.lidar_path
        if not lidar_file:
            logger.error("No LiDAR file selected.")
            QMessageBox.critical(self, "Error", "Please select a LiDAR file.")
            return

        study_area = self.set_proj_area_gdf(self.proj_area_poly)
        if study_area is None:
            logger.error("Failed to load the project area GeoDataFrame.")
            QMessageBox.critical(self, "Error", "Failed to load the project area.")
            return

        # Ensure sys.stdout is not None
        if sys.stdout is None:
            sys.stdout = open(os.devnull, 'w')
       
        process = None

        # Initialize Progress Dialog
        progress_dialog = QDialog()
        ui = ProgressDialog()
        ui.setupUi(progress_dialog)

        # Set initial progress value and clear output text
        ui.progressBar.setValue(0)
        ui.progress_state.clear()
        progress_dialog.show()

        try:
            # Start the process and update progress
            ui.progress_state.append("Initializing WhiteboxTools...")
            QApplication.processEvents()

            wbt = whitebox.WhiteboxTools()

            ui.progress_state.append("Running LiDAR IDW Interpolation...")
            ui.progressBar.setValue(20)  # Update progress
            QApplication.processEvents()
            
            # Here we assume the process is successfully started
            if process:
                process.wait()  # Wait for the process to complete
                logger.info("WhiteboxTools process completed successfully.")
            
            # Update progress to show canopy creations
            ui.progress_state.setTesxt("Creating first and second return geodataframes.")
            ui.progressBar.setValue(35)
            QApplication.processEvents()

            canopy_gdf = process_lidar_to_canopy(study_area, lidar_file, canopy_height=5)
            
            output_path = os.path.join(self.output_dir, "lidar_canopy_output")
            if not os.path.exists(output_path):
                os.makedirs(output_path)

            # Update progress and continue with canopy processing
            ui.progress_state.setText("Processing canopy areas...")
            ui.progressBar.setValue(50)
            QApplication.processEvents()

            process_canopy_areas(canopy_gdf, 
                                os.path.basename(self.output_dir),  # Corrected lambda usage
                                study_area, 
                                output_path,
                                buffer_distance=5)
            
            # Update progress and prompt user to load shapefiles
            ui.progress_state.setText("Finalizing and preparing output...")
            ui.progressBar.setValue(80)
            QApplication.processEvents()

            # Show a dialog to let the user choose which shapefiles to load
            shapefiles = [os.path.join(output_path, f) for f in os.listdir(output_path) if f.endswith('.shp')]
            selected_shapefiles = self.prompt_load_shapefiles(shapefiles)

            if selected_shapefiles:
                for shapefile in selected_shapefiles:
                    self.load_polygon_to_qgis(shapefile, os.path.basename(shapefile))
                ui.progress_state.setText("Shapefiles loaded into QGIS.")
            else:
                ui.progress_state.setText("No shapefiles were loaded.")

            ui.progressBar.setValue(100)  # Update progress to completion
            progress_dialog.accept()

            # User feedback on successful processing
            QMessageBox.information(self, "Success", "LiDAR processing complete.")

        except Exception as e:
            logger.error("An error occurred during LiDAR processing.", exc_info=True)
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            progress_dialog.reject()

        finally:
            if process:
                try:
                    if process.poll() is None:  # Check if the process is still running
                        logger.warning("Process still running. Terminating...")
                        process.terminate()
                    if process.stdout:
                        process.stdout.close()
                    if process.stderr:
                        process.stderr.close()
                except Exception as e:
                    logger.error("An error occurred while managing the process.", exc_info=True)


    def prompt_load_shapefiles(self, shapefiles):
        """
        Prompt the user to select which shapefiles to load into QGIS.
        :param shapefiles: List of shapefile paths.
        :return: List of selected shapefiles.
        """
        items, ok = QInputDialog.getItem(self, "Select Shapefiles", 
                                        "Choose shapefiles to load (Ctrl+click to select multiple):", 
                                        shapefiles, 0, True)

        if ok and items:
            return items
        return []

    def load_polygon_to_qgis(self, shapefile_path, layer_name):
        """
        Load a polygon shapefile into QGIS.
        :param shapefile_path: Path to the shapefile.
        :param layer_name: Name for the QGIS layer.
        """
        layer = QgsVectorLayer(shapefile_path, layer_name, "ogr")
        if not layer.isValid():
            QMessageBox.critical(self, "Error", f"Failed to load shapefile: {shapefile_path}")
            return
        QgsProject.instance().addMapLayer(layer)
        logger.info(f"Loaded shapefile into QGIS: {shapefile_path}")

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
