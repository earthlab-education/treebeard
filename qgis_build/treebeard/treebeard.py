import os
import logging
import subprocess
import sys
import traceback

import geopandas as gpd
import numpy as np
from qgis.PyQt.QtWidgets import QApplication, QFileDialog, QDialog, QAction, QMessageBox, QInputDialog
from qgis.PyQt.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QDialogButtonBox,  QLabel,  QListWidget, QListWidgetItem, QMessageBox, QVBoxLayout
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry
from PyQt5 import QtCore, QtGui, QtWidgets 
from PyQt5.QtCore import Qt,  QVariant, QCoreApplication
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
from .segment_drapp import KMeansProcessor 
from .shp_select import Ui_Dialog as ShpSelect

# COLO_CRS = "EPSG:6430"

# Ensure OSGeo4W QGIS path loaded first
import sys
sys.path.insert(0, r'C:\PROGRA~1\QGIS33~1.10\apps\Python312\Lib\site-packages')


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
        ui =  ImportRasterDialog()
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
            # Create a simple dialog to select a raster layer
            select_dialog = QDialog(self)
            select_dialog.setWindowTitle("Select QGIS Raster Layer")
            
            layout = QVBoxLayout(select_dialog)
            label = QLabel("Select a raster layer from the loaded QGIS layers:", select_dialog)
            layout.addWidget(label)

            # Create a list widget to show available raster layers
            layer_list_widget = QListWidget(select_dialog)
            layout.addWidget(layer_list_widget)

            # Populate the list widget with available raster layers
            layers = QgsProject.instance().mapLayers().values()
            for layer in layers:
                if isinstance(layer, QgsRasterLayer):
                    layer_list_widget.addItem(layer.name())

            # Create OK and Cancel buttons
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, select_dialog)
            layout.addWidget(button_box)

            # Handle button clicks
            button_box.accepted.connect(select_dialog.accept)
            button_box.rejected.connect(select_dialog.reject)

            # Show the dialog and get the result
            if select_dialog.exec_() == QDialog.Accepted:
                selected_items = layer_list_widget.selectedItems()
                if selected_items:
                    selected_layer_name = selected_items[0].text()
                    selected_layer = QgsProject.instance().mapLayersByName(selected_layer_name)
                    if selected_layer:
                        self.raster_path = selected_layer[0].source()
                    else:
                        QMessageBox.critical(self, "Error", "Selected layer not found.")
                else:
                    QMessageBox.critical(self, "Error", "No layer selected.")
        
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
            ui.progress_state.setText("Initializing WhiteboxTools...")
            QApplication.processEvents()

            wbt = whitebox.WhiteboxTools()

            ui.progress_state.setText("Running LiDAR IDW Interpolation...")
            ui.progressBar.setValue(20)  # Update progress
            QApplication.processEvents()
            
            # Here we assume the process is successfully started
            if process:
                process.wait()  # Wait for the process to complete
                logger.info("WhiteboxTools process completed successfully.")
            
            # Update progress to show canopy creations
            ui.progress_state.setText("Creating first and second return geodataframes.")
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
            selected_shapefiles = self.show_shp_files(shapefiles)

 

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



    def show_shp_files(self, shapefiles):
        """Show a dialog for the user to select which shapefiles to load into QGIS."""
        dialog = QDialog()
        ui = ShpSelect()
        ui.setupUi(dialog)

        # Add shapefiles to the QListWidget
        for shapefile in shapefiles:
            item = QListWidgetItem(os.path.basename(shapefile))
            item.setData(QtCore.Qt.UserRole, shapefile)
            item.setCheckState(QtCore.Qt.Unchecked)
            ui.listWidget.addItem(item)

        # Show dialog and handle user selection
        if dialog.exec_() == QDialog.Accepted:
            selected_files = [ui.listWidget.item(i).data(QtCore.Qt.UserRole) 
                            for i in range(ui.listWidget.count()) 
                            if ui.listWidget.item(i).checkState() == QtCore.Qt.Checked]
            self.load_shp_file(selected_files)

    def load_shp_file(self, shapefiles):
        """Load the selected shapefiles into QGIS."""
        for shapefile in shapefiles:
            layer = QgsVectorLayer(shapefile, os.path.basename(shapefile), "ogr")
            if not layer.isValid():
                QMessageBox.critical(self, "Error", f"Failed to load shapefile: {shapefile}")
            QgsProject.instance().addMapLayer(layer)
            logger.info(f"Shapefile loaded: {shapefile}")


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
    
    def process_kmeans(self):
        """Run K-means processing on aerial photography or GeoTIFF raster file."""
        
        tilepath = self.raster_path
        if tilepath is None:
            logger.error("No Aerial Photography file selected.")
            QMessageBox.critical(self, "Error", "Please select aerial photograph or GeoTIFF raster file.")
            return

        # Initialize Progress Dialog
        progress_dialog = QDialog()
        ui = ProgressDialog()
        ui.setupUi(progress_dialog)

        # Set initial progress value and clear output text
        ui.progressBar.setValue(0)
        ui.progress_state.setText("Initializing K-means processing...")
        progress_dialog.show()

        try:
            processor = KMeansProcessor()
            
            # Update progress and call the generate_binary_gdf_ndvi function
            ui.progress_state.setText("Generating NDVI-based binary GeoDataFrame...")
            QApplication.processEvents()
            dissolved_gdf = processor.generate_binary_gdf_ndvi(tilepath, 
                                                               n_clusters=2, 
                                                               plot_segments=False)
            ui.progressBar.setValue(70)

            # Save the output shapefile
            output_shapefile = os.path.join(self.output_dir, "kmeans_output.shp")
            dissolved_gdf.to_file(output_shapefile)
            ui.progress_state.setText(f"K-means processing completed. Output saved to {output_shapefile}")
            ui.progressBar.setValue(100)
            QApplication.processEvents()

        except Exception as e:
            logger.error("An error occurred during K-means processing.", exc_info=True)
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

        finally:
            progress_dialog.accept()

    
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
        icon_path = os.path.join(self.plugin_dir, 'icon-test1.png')
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
