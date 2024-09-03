import earthpy.spatial as es
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import unary_union
from skimage import io, color
from skimage.segmentation import quickshift
from sklearn.cluster import KMeans
from tqdm import tqdm
import os

class KMeansProcessor():
    
    def generate_binary_gdf_ndvi(self, tilepath,
                                  n_clusters=2, 
                                  plot_segments=False, 
                                  plot_path=None, 
                                  output_shapefile_path=None, 
                                  apply_buffering=False, buffer_size=5):
        """Generates a segmented K-Means polygon and optionally applies buffering."""

        # Load the image and bands
        tile = rasterio.open(tilepath)
        red = tile.read(1).astype(float)
        nir = tile.read(4).astype(float)

        # Get image bounding box info
        sr = tile.crs
        affine = tile.transform

        # Compute NDVI
        ndvi = es.normalized_diff(nir, red)
        ndvi = np.where(np.isnan(ndvi), 0, ndvi)

        # Segment the NDVI image using quickshift
        img = io.imread(tilepath)
        img_ndvi = np.expand_dims(ndvi, axis=2).astype(np.float32)
        segments = quickshift(img_ndvi, 
                              kernel_size=3, 
                              convert2lab=False, 
                              max_dist=6, 
                              ratio=0.5).astype('int32')
        
        print("Quickshift number of segments: %d" % len(np.unique(segments)))

        if plot_segments and plot_path:
            # Plot and save segments
            self.plot_segments(img, ndvi, segments, plot_path)

        # Convert segments to vector features
        polys = [shape(shp) for shp, value in tqdm(shapes(segments, transform=affine), 
                                                   desc="Converting segments to vector features")]

        # Compute mean NDVI for each segment
        mean_ndvi_vals = np.array([ndvi[rasterio.features.geometry_mask([shp], 
                                                                        transform=affine, 
                                                                        invert=True, 
                                                                        out_shape=ndvi.shape)]
                                                                        .mean() 
                                                                        for shp in polys]).reshape(-1, 1)

        # Apply K-Means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit(mean_ndvi_vals)
        labels = kmeans.labels_

        # Create GeoDataFrame with segments and their cluster labels
        gdf = gpd.GeoDataFrame({'geometry': polys, 'cluster': labels}, crs=sr)

        # Determine which cluster corresponds to 'tree' based on NDVI values
        cluster_mean_ndvi = [mean_ndvi_vals[labels == i].mean() for i in range(n_clusters)]
        tree_cluster_idx = np.argmax(cluster_mean_ndvi)
        gdf['class'] = gdf['cluster'].apply(lambda x: 1 if x == tree_cluster_idx else 0)

        # Dissolve polygons by 'class' to merge connected polygons
        dissolved_gdfs = []
        for cls in tqdm(gdf['class'].unique(), desc="Dissolving polygons by class"):
            class_gdf = gdf[gdf['class'] == cls]
            dissolved_gdf = class_gdf.dissolve()
            dissolved_gdf['class'] = cls
            dissolved_gdfs.append(dissolved_gdf)

        # Combine the dissolved GeoDataFrames
        dissolved_gdf = gpd.GeoDataFrame(pd.concat(dissolved_gdfs, ignore_index=True), crs=sr)

        if apply_buffering:
            # Apply buffering if requested
            bounds_gdf = self.get_bounds_gdf(tilepath)
            dissolved_gdf, _ = self.apply_buffer(dissolved_gdf, bounds_gdf, buffer_size)

        if output_shapefile_path:
            # Save the GeoDataFrame as a shapefile
            dissolved_gdf.to_file(output_shapefile_path, driver="ESRI Shapefile")
            print(f"Shapefile saved to {output_shapefile_path}")

        return dissolved_gdf

    def plot_segments(self, img, ndvi, segments, plot_path):
        """Plot and save segments, NDVI, and classified clusters."""
        rgb_img = img[:, :, :3]
        segment_means = np.zeros_like(ndvi)
        for seg_val in np.unique(segments):
            segment_means[segments == seg_val] = ndvi[segments == seg_val].mean()
        plt.imshow(segment_means, cmap='RdYlGn')
        plt.title("NDVI Mean by Segments")
        plt.axis('off')
        plt.savefig(f"{plot_path}_ndvi_mean_by_segments.png")
        plt.close()

    def get_bounds_gdf(self, geotiff_path):
        """Get bounding box as a GeoDataFrame."""
        tile = rasterio.open(geotiff_path)
        bounds = tile.bounds
        minx, miny, maxx, maxy = bounds
        bounds_poly = Polygon([(minx, miny), (minx, maxy), (maxx, maxy), (maxx, miny)])
        return gpd.GeoDataFrame(geometry=[bounds_poly], crs=tile.crs)

    def apply_buffer(self, canopy_gdf, bounds_gdf, buffer_size=5):
        """Apply buffering and return buffered polygons."""
        canopy_buffer = canopy_gdf.buffer(buffer_size)
        buffered_gdf = gpd.GeoDataFrame(geometry=canopy_buffer, crs=canopy_gdf.crs)
        canopy_buffer_clipped = gpd.clip(buffered_gdf, bounds_gdf)
        return canopy_buffer_clipped, None  # Return clipped buffered polygons
