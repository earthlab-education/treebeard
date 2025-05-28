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
        """Generates a segmented K-Means polygon from NDVI, classifies it, and optionally buffers and saves it."""

        import pandas as pd
        from sklearn.cluster import KMeans
        from rasterio.features import shapes
        from skimage.segmentation import quickshift
        from skimage import io
        import earthpy.spatial as es
        from tqdm import tqdm
        import rasterio

            # Load the image and bands
        tile = rasterio.open(tilepath)
        red = tile.read(1).astype(float)
        nir = tile.read(4).astype(float)
        affine = tile.transform
        sr = tile.crs

        # Compute NDVI and handle NaNs
        ndvi = es.normalized_diff(nir, red)
        ndvi = np.where(np.isnan(ndvi), 0, ndvi)

        # Segment NDVI using quickshift
        img = io.imread(tilepath)
        img_ndvi = np.expand_dims(ndvi, axis=2).astype(np.float32)
        segments = quickshift(img_ndvi, kernel_size=3, convert2lab=False, max_dist=6, ratio=0.5).astype('int32')
        
        print(f"Quickshift number of segments: {len(np.unique(segments))}")

        # Optional: save segment image
        if plot_segments and plot_path:
            self.plot_segments(img, ndvi, segments, plot_path)

        # Efficient mean NDVI calculation per segment using vectorized grouping
        flat_segments = segments.flatten()
        flat_ndvi = ndvi.flatten()
        import pandas as pd
        df = pd.DataFrame({'segment': flat_segments, 'ndvi': flat_ndvi})
        mean_ndvi_per_segment = df.groupby('segment')['ndvi'].mean()

        # Convert segments to polygons
        polys = []
        segment_ids = []
        for shp, val in tqdm(shapes(segments, transform=affine), desc="Converting segments to vector features"):
            polys.append(shape(shp))
            segment_ids.append(val)

        # Create GeoDataFrame with geometry and segment ID
        gdf = gpd.GeoDataFrame({'geometry': polys, 'segment': segment_ids}, crs=sr)

        # Map mean NDVI values to each polygon using segment ID
        gdf['mean_ndvi'] = gdf['segment'].map(mean_ndvi_per_segment)

        # KMeans clustering based on mean NDVI per polygon
        from sklearn.cluster import KMeans
        mean_ndvi_vals = gdf['mean_ndvi'].values.reshape(-1, 1)
        kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit(mean_ndvi_vals)
        gdf['cluster'] = kmeans.labels_

        # Determine which cluster is 'tree' (highest mean NDVI)
        cluster_means = [mean_ndvi_vals[gdf['cluster'] == i].mean() for i in range(n_clusters)]
        tree_cluster_idx = np.argmax(cluster_means)

        # Assign class labels: 1 = tree/canopy, 0 = open space
        gdf['class'] = gdf['cluster'].apply(lambda x: 1 if x == tree_cluster_idx else 0)

        # Dissolve polygons by class to merge connected polygons
        dissolved_gdf = gdf.dissolve(by='class', as_index=False)

        # Optional buffering
        if apply_buffering:
            bounds_gdf = self.get_bounds_gdf(tilepath)
            dissolved_gdf, _ = self.apply_buffer(dissolved_gdf, bounds_gdf, buffer_size)

        # Optional save to shapefile
        if output_shapefile_path:
            dissolved_gdf.to_file(output_shapefile_path, driver="ESRI Shapefile")
            print(f"Shapefile saved to {output_shapefile_path}")

        return dissolved_gdf
    
    def plot_binary_gdf(self, dissolved_gdf, filepath=None, save_png_file=False):
        """
        Plots the binary GeoDataFrame showing classified clusters (Tree and Not Tree).

        Parameters:
        - dissolved_gdf (GeoDataFrame): The GeoDataFrame containing classified clusters.
        - filepath (str): Path to save the plot (optional).
        - save_png_file (bool): Whether to save the plot as a PNG file (default is False).
        """
        # Add a new column for categorical labels
        dissolved_gdf['category'] = dissolved_gdf['class'].map({1: 'Tree', 0: 'Not Tree'})

        fig, ax = plt.subplots(figsize=(10, 10))

        # Remove axis labels, ticks, and tick labels
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.tick_params(axis='both', which='both', length=0)

        dissolved_gdf.plot(column='category',
                        ax=ax, legend=True, cmap='viridis',
                        legend_kwds={'title': "Class"})
        plt.title("Classified Clusters (Tree and Not Tree)")

        if save_png_file:
            plt.savefig(filepath)

        plt.show()

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


    def multipolygons_to_polygons(self, dissolved_gdf):
        polygons = []
        classes = []
        for idx, row in dissolved_gdf.iterrows():
            if isinstance(row.geometry, MultiPolygon):
                for poly in row.geometry.geoms:  # Corrected line
                    polygons.append(poly)
                    classes.append(row['class'])
            else:
                polygons.append(row.geometry)
                classes.append(row['class'])
        return gpd.GeoDataFrame({'geometry': polygons, 'class': classes}, crs=dissolved_gdf.crs)


    def classless_multipolygons_to_polygons(self, gdf):
        polygons = []
        for idx, row in gdf.iterrows():
            if isinstance(row.geometry, MultiPolygon):
                for poly in row.geometry.geoms:
                    polygons.append(poly)
            else:
                polygons.append(row.geometry)
        return gpd.GeoDataFrame({'geometry': polygons}, crs=gdf.crs)
    
    def calculate_area(self, gdf):
        # Calculate area in square feet and acres
        gdf['area_feet'] = gdf.geometry.area
        gdf['area_acres'] = gdf['area_feet'] / 43560

        # Define a function to categorize the gap size
        def categorize_gap_size(acres):
            if acres < 1/8:
                return '< 1/8 acre'
            elif 1/8 <= acres < 1/4:
                return '1/8 - 1/4 acre'
            elif 1/4 <= acres < 1/2:
                return '1/4 - 1/2 acre'
            elif 1/2 <= acres < 1:
                return '1/2 - 1 acre'
            else:
                return '> 1 acre'

        # Apply the categorization function to the 'area_acres' column
        gdf['gap_size_category'] = gdf['area_acres'].apply(categorize_gap_size)

        return gdf

    # Function to bin and plot the areas
    def save_bin_plot(self, gdf, bins, labels, title, filepath=None, save_png_file=False):
        gdf['bin'] = pd.cut(gdf['area_acres'], bins=bins, labels=labels, right=False)
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))

        # Remove axis labels, ticks, and tick labels
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.tick_params(axis='both', which='both', length=0)

        plot = gdf.plot(column='bin', ax=ax, legend=True, categorical=True, legend_kwds={'title': 'Size Category'})
        # plot = gdf.plot(column='bin', ax=ax, legend=True, categorical=True, 
        #                 legend_kwds={'title': 'Size Category'}, edgecolor='black')
        ax.set_title(title)
        plt.tight_layout()
        filename = title.split('.')[0]
        plt.savefig(f'{filename}.png')

        if save_png_file:
            plt.savefig(filepath)
        
        plt.show()


    def plot_gdf(self, gdf, title, filepath=None, save_png_file=False):
        fig, ax = plt.subplots(figsize=(10, 10))
        # Remove axis labels, ticks, and tick labels
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.tick_params(axis='both', which='both', length=0)
        gdf.plot(ax=ax, color='lightblue', edgecolor='black')
        plt.title(title)

        if save_png_file:
            plt.savefig(filepath)

        plt.show()


    def get_bounds_gdf(self, geotiff_path):
        tile = rasterio.open(geotiff_path)
        bounds = tile.bounds
        minx, miny, maxx, maxy = bounds
        bounds_poly = Polygon([(minx, miny), (minx, maxy), (maxx, maxy), (maxx, miny)])
        gdf = gpd.GeoDataFrame(geometry=[bounds_poly], crs=tile.crs)
        return gdf


    def apply_buffer(self, canopy_gdf, bounds_gdf, buffer_size=5):
        """
        Creates two GeoDataFrames: one for buffered canopy polygons and one for open space polygons.

        Parameters:
        - canopy_gdf: GeoDataFrame containing canopy polygons.
        - bounds_gdf: GeoDataFrame containing the bounds to clip the buffered canopy polygons.
        - buffer_size: The size of the buffer to apply to the canopy polygons (default is 5 feet).

        Returns:
        - buffered_gdf: GeoDataFrame containing buffered canopy polygons.
        - openspace_gdf: GeoDataFrame containing open space polygons.
        """

        # Buffer the canopy polygons by the specified buffer size
        canopy_buffer = canopy_gdf.buffer(buffer_size)

        # Create a GeoDataFrame from the buffered canopy polygons
        buffered_gdf = gpd.GeoDataFrame(geometry=canopy_buffer, crs=canopy_gdf.crs)

        # Clip the buffered canopy polygons to the original bounds
        canopy_buffer_clipped = gpd.clip(buffered_gdf, bounds_gdf)

        # Create a unary union of the clipped buffer polygons
        buffer_union = unary_union(canopy_buffer_clipped.geometry)

        # Invert the buffer to get the open space polygons
        openspace_polygons = bounds_gdf.geometry.difference(buffer_union)

        # Create a GeoDataFrame for the open space polygons
        openspace_gdf = gpd.GeoDataFrame(geometry=openspace_polygons, crs=bounds_gdf.crs)

        return buffered_gdf, openspace_gdf
    
    def process_canopy_areas_imagery(self, canopy_gdf, proj_area_name, study_area, output_path, buffer_distance=5):
        """
        Processes canopy areas by buffering, dissolving, clipping, and exploding the geometries.
        Adds acreage and size category columns.

        Parameters
        ----------
        canopy_gdf : gpd.GeoDataFrame
            GeoDataFrame representing canopy areas.
        study_area : gpd.GeoDataFrame
            GeoDataFrame representing the boundary within which to clip the canopy areas.
        output_path : path
            File path to output processed shapefiles
        buffer_distance : float, optional
            The distance to buffer the canopy geometries. Default is 5 units.

        Returns
        -------
        clipped_buffer : gpd.GeoDataFrame
            GeoDataFrame with the buffered and clipped canopy areas.
        exploded_gap_gdf : gpd.GeoDataFrame
            GeoDataFrame with exploded geometries representing non-tree canopy areas, including acreage and size category.
        """
        # Ensure study area CRS is the same as the processed canopy CRS (should be in Feet)
        study_area = study_area.to_crs(canopy_gdf.crs)

        # Ensure input GeoDataFrames have CRS
        if canopy_gdf.crs is None or study_area.crs is None:
            raise ValueError("Input GeoDataFrames must have a CRS defined.")

        # Buffer the canopy geometries
        buffered_canopy = canopy_gdf.geometry.buffer(buffer_distance)

        # Create a new GeoDataFrame with the buffered geometries
        buffer_gdf = gpd.GeoDataFrame(geometry=buffered_canopy, crs=canopy_gdf.crs)

        # Dissolve the buffered geometries into a single MultiPolygon
        dissolved_canopy = unary_union(buffer_gdf.geometry)

        # Convert the dissolved canopy back to a GeoDataFrame
        dissolved_canopy_gdf = gpd.GeoDataFrame(geometry=[dissolved_canopy], crs=canopy_gdf.crs)

        # Clip the dissolved canopy with the study area
        clipped_buffer = gpd.overlay(dissolved_canopy_gdf, study_area, how='intersection')

        # Calculate the difference between the study area and the clipped buffer
        non_tree_canopy_gdf = gpd.overlay(study_area, clipped_buffer, how='difference')

        # Explode multipart polygon to prepare for area calculations
        exploded_gap_gdf = non_tree_canopy_gdf.explode(index_parts=True)

        # Reset the index to have a clean DataFrame
        exploded_gap_gdf.reset_index(drop=True, inplace=True)

        # Calculate the area in acres (1 acre = 43,560 square feet)
        exploded_gap_gdf['Acreage'] = exploded_gap_gdf.geometry.area / 43560

        # Define a function to categorize the gap size
        def categorize_gap_size(acres):
            if acres < 1/8:
                return '< 1/8 acre'
            elif 1/8 <= acres < 1/4:
                return '1/8 - 1/4 acre'
            elif 1/4 <= acres < 1/2:
                return '1/4 - 1/2 acre'
            elif 1/2 <= acres < 1:
                return '1/2 - 1 acre'
            else:
                return '> 1 acre'

        # Apply the categorization function to the Acreage column
        exploded_gap_gdf['Gap_Size_Category'] = exploded_gap_gdf['Acreage'].apply(categorize_gap_size)

        # Output shapefiles

        canopy_gaps_calced_path = os.path.join(output_path,'imagery_'+ proj_area_name + '_canopy_gaps_calced.shp')
        exploded_gap_gdf.to_file(canopy_gaps_calced_path)
        dissolved_canopy_path = os.path.join(output_path, 'imagery_'+ proj_area_name + '_canopy.shp')
        canopy_gdf.to_file(dissolved_canopy_path)
        buffered_canopy_path = os.path.join(output_path,'imagery_'+ proj_area_name + '_buffered_canopy.shp')
        clipped_buffer.to_file(buffered_canopy_path)