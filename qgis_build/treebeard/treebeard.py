import sys
import os
from qgis.PyQt.QtWidgets import QAction, QDialog, QFileDialog, QMessageBox
from qgis.PyQt.QtGui import QIcon
from PyQt5.QtCore import QCoreApplication, QVariant
from .treebeard_dialog import treebeardDialog
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry

# Import numpy from QGIS environment
try:
    import numpy as np
except ImportError:
    raise ImportError("Numpy is not installed in the QGIS Python environment. Please install it using the QGIS Python interpreter.")

# Add the extlibs directory to sys.path
plugin_dir = os.path.dirname(__file__)
extlibs_path = os.path.join(plugin_dir, 'extlibs')
if extlibs_path not in sys.path:
    sys.path.append( extlibs_path)

# Remove the folder from its current position in sys.path if it exists
if extlibs_path in sys.path:
    sys.path.remove(extlibs_path)

# Append the folder to the end of sys.path
sys.path.append(extlibs_path)

# Now import other dependencies
try:
    # import fiona
    # import geopandas as gpd
    # import rasterio
    from sklearn.cluster import KMeans
except ImportError as e:
    raise ImportError(f"An import error occurred: {e}. Ensure all dependencies are installed in the QGIS Python environment.")


class Treebeard:
    def __init__(self, iface):
        self.iface = iface  # QGIS interface
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
        dialog.show()
        dialog.exec_()

class TreebeardDialog(treebeardDialog):
    def __init__(self, parent=None):
        super(TreebeardDialog, self).__init__(parent)
        self.setupUi(self)
        self.browseRasterButton.clicked.connect(self.browse_raster_file)
        self.browsePolygonButton.clicked.connect(self.browse_polygon_file)
        self.processButton.clicked.connect(self.process_files)
        self.raster_path = ""
        self.polygon_path = ""

    def browse_raster_file(self):
        self.raster_path, _ = QFileDialog.getOpenFileName(self, "Select Raster File", "", "Raster files (*.tif)")
        if self.raster_path:
            self.rasterLineEdit.setText(self.raster_path)

    def browse_polygon_file(self):
        self.polygon_path, _ = QFileDialog.getOpenFileName(self, "Select Boundary Polygon File", "", "Vector files (*.shp *.geojson)")
        if self.polygon_path:
            self.polygonLineEdit.setText(self.polygon_path)

    def process_files(self):
        if not self.raster_path or not self.polygon_path:
            QMessageBox.critical(self, "Error", "Please select both raster and polygon files.")
            return

        try:
            cluster_labels, profile = self.kmeans_clustering(self.raster_path, n_clusters=4)
            gdf_clusters = self.clusters_to_polygons(cluster_labels, profile, self.polygon_path)
            self.load_polygons_to_qgis(gdf_clusters, "Clustered Polygons")
            self.calculate_spatial_statistics(gdf_clusters)
            QMessageBox.information(self, "Success", "Processing complete.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

'''
    def kmeans_clustering(self, raster_path, n_clusters=4):
        with rasterio.open(raster_path) as src:
            bands = [src.read(i) for i in range(1, src.count + 1)]
            image_data = np.dstack(bands)

        pixels = image_data.reshape((-1, image_data.shape[2]))
        kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=10)
        kmeans.fit(pixels)
        labels = kmeans.labels_.reshape(image_data.shape[:2])

        return labels, src.profile

    def clusters_to_polygons(self, cluster_labels, profile, polygon_path):
        with fiona.open(polygon_path, "r") as shapefile:
            shapes_polygon = [feature["geometry"] for feature in shapefile]

        mask = cluster_labels != 0
        results = (
            {'properties': {'cluster': int(v)}, 'geometry': s}
            for i, (s, v) in enumerate(shapes(cluster_labels, mask=mask, transform=profile['transform']))
        )

        geoms = list(results)
        gdf_clusters = gpd.GeoDataFrame.from_features(geoms)
        gdf_clusters.crs = profile['crs']

        gdf_polygons = gpd.read_file(polygon_path)
        gdf_clusters = gpd.overlay(gdf_clusters, gdf_polygons, how='intersection')

        return gdf_clusters

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
'''