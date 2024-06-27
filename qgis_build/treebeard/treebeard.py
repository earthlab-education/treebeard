import sys
import os

# Get the directory of the current file
plugin_dir = os.path.dirname(__file__)

# Add the extlibs directory to sys.path
extlibs_path = os.path.join(plugin_dir, 'extlibs')
if extlibs_path not in sys.path:
    sys.path.insert(0, extlibs_path)

# Now you can import your dependencies as usual
# import fiona
# import geopandas as gpd
# import numpy as np
# import rasterio
# from sklearn.cluster import KMeans
# import shapely

from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox, QDialog
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, QgsVectorDataProvider
from PyQt5.QtCore import QVariant
from .ui_treebeard_test import Ui_TreebeardDialogBase

class TreebeardDialog(QDialog, Ui_TreebeardDialogBase):
    def __init__(self, parent=None):
        """
        Constructor for the dialog class.
        :param parent: Parent widget.
        """
        super(TreebeardDialog, self).__init__(parent)
        self.setupUi(self)
        self.browseRasterButton.clicked.connect(self.browse_raster_file)
        self.browsePolygonButton.clicked.connect(self.browse_polygon_file)
        self.processButton.clicked.connect(self.process_files)
        self.raster_path = ""
        self.polygon_path = ""

    def browse_raster_file(self):
        """
        Browse and select a raster file.
        """
        self.raster_path, _ = QFileDialog.getOpenFileName(self, "Select Raster File", "", "Raster files (*.tif)")
        if self.raster_path:
            self.rasterLineEdit.setText(self.raster_path)

    def browse_polygon_file(self):
        """
        Browse and select a boundary polygon file.
        """
        self.polygon_path, _ = QFileDialog.getOpenFileName(self, "Select Boundary Polygon File", "", "Vector files (*.shp *.geojson)")
        if self.polygon_path:
            self.polygonLineEdit.setText(self.polygon_path)

    # def process_files(self):
    #     """
    #     Process the selected files.
    #     """
    #     if not self.raster_path or not self.polygon_path:
    #         QMessageBox.critical(self, "Error", "Please select both raster and polygon files.")
    #         return

    #     try:
    #         cluster_labels, profile = self.kmeans_clustering(self.raster_path, n_clusters=4)
    #         gdf_clusters = self.clusters_to_polygons(cluster_labels, profile, self.polygon_path)
    #         self.load_polygons_to_qgis(gdf_clusters, "Clustered Polygons")
    #         self.calculate_spatial_statistics(gdf_clusters)
    #         QMessageBox.information(self, "Success", "Processing complete.")
    #     except Exception as e:
    #         QMessageBox.critical(self, "Error", str(e))

    # def kmeans_clustering(self, raster_path, n_clusters=4):
    #     """
    #     Perform k-means clustering on the raster file.
    #     :param raster_path: Path to the raster file.
    #     :param n_clusters: Number of clusters.
    #     :return: Cluster labels and raster profile.
    #     """
    #     with rasterio.open(raster_path) as src:
    #         bands = [src.read(i) for i in range(1, src.count + 1)]
    #         image_data = np.dstack(bands)

    #     pixels = image_data.reshape((-1, image_data.shape[2]))
    #     kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=10)
    #     kmeans.fit(pixels)
    #     labels = kmeans.labels_.reshape(image_data.shape[:2])

    #     return labels, src.profile

    # def clusters_to_polygons(self, cluster_labels, profile, polygon_path):
    #     """
    #     Convert cluster labels to polygons.
    #     :param cluster_labels: Cluster labels from k-means.
    #     :param profile: Raster profile.
    #     :param polygon_path: Path to the polygon file.
    #     :return: GeoDataFrame of clusters.
    #     """
    #     with fiona.open(polygon_path, "r") as shapefile:
    #         shapes_polygon = [feature["geometry"] for feature in shapefile]

    #     mask = cluster_labels != 0
    #     results = (
    #         {'properties': {'cluster': int(v)}, 'geometry': s}
    #         for i, (s, v) in enumerate(shapes(cluster_labels, mask=mask, transform=profile['transform']))
    #     )

    #     geoms = list(results)
    #     gdf_clusters = gpd.GeoDataFrame.from_features(geoms)
    #     gdf_clusters.crs = profile['crs']

    #     gdf_polygons = gpd.read_file(polygon_path)
    #     gdf_clusters = gpd.overlay(gdf_clusters, gdf_polygons, how='intersection')

    #     return gdf_clusters

    def load_polygons_to_qgis(self, gdf, layer_name='Clustered Polygons'):
        """
        Load polygons into QGIS.
        :param gdf: GeoDataFrame of clusters.
        :param layer_name: Name of the QGIS layer.
        """
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
        """
        Calculate spatial statistics for the clusters.
        :param gdf: GeoDataFrame of clusters.
        """
        stats = gdf['geometry'].area.describe()
        print("Spatial Statistics:")
        print(stats)


class Treebeard:
    def __init__(self, iface):
        """
        Constructor for the main plugin class.
        :param iface: An interface instance that will be passed to this class.
        """
        self.iface = iface  # QGIS interface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = self.tr(u'&Treebeard')
        self.first_start = None

    def tr(self, message):
        """
        Get the translation for a string using Qt translation API.
        :param message: String to translate.
        :return: Translated string.
        """
        return QCoreApplication.translate('Treebeard', message)

    def initGui(self):
        """
        Initialize the GUI, adding menu items and toolbar icons.
        """
        icon_path = ':/plugins/treebeard/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Treebeard'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )

    def add_action(self, 
                   icon_path, 
                   text, 
                   callback, 
                   enabled_flag=True, 
                   add_to_menu=True, 
                   add_to_toolbar=True, 
                   status_tip=None, 
                   whats_this=None, 
                   parent=None):
        """
        Add an action to the plugin's menu and toolbar.
        :param icon_path: Path to the icon for this action.
        :param text: Text for the action.
        :param callback: Function to call when the action is triggered.
        :param enabled_flag: Initial enabled state of the action.
        :param add_to_menu: True to add to the menu, False otherwise.
        :param add_to_toolbar: True to add to the toolbar, False otherwise.
        :param status_tip: Optional status tip for the action.
        :param whats_this: Optional "What's this?" help message.
        :param parent: Parent widget for the action.
        :return: The action that was created.
        """
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
        """
        Remove the plugin's menu items and icons.
        """
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&Treebeard'), action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """
        Run method that performs all the real work.
        """
        dialog = TreebeardDialog()
        dialog.exec_()

