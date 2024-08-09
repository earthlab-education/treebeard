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


def generate_binary_gdf_ndvi(tilepath, n_clusters=2, plot_segments=False, plot_path=None):
    """
    Generates a GeoDataFrame with two classes: 'tree' and 'not tree' based on NDVI values.

    Parameters:
    - tilepath (str): Path to the GeoTIFF image.
    - n_clusters (int): Number of clusters to use in KMeans clustering (default is 2).
    - plot_segments (bool): Whether to plot the quickshift segments (default is False).
    - plot_path (str): Path to save the segment plots (optional).

    Returns:
    - GeoDataFrame: A dissolved GeoDataFrame with polygons classified as 'tree' or 'not tree'.
    """
    # Load the image and bands
    tile = rasterio.open(tilepath)
    red = tile.read(1).astype(float)
    nir = tile.read(4).astype(float)

    # Get image bounding box info
    sr = tile.crs
    bounds = tile.bounds
    affine = tile.transform

    # Compute NDVI using earthpy.spatial.normalized_diff
    ndvi = es.normalized_diff(nir, red)

    # Handle NaN values
    ndvi = np.where(np.isnan(ndvi), 0, ndvi)

    # Segment the NDVI image using quickshift
    img = io.imread(tilepath)
    img_ndvi = np.expand_dims(ndvi, axis=2).astype(np.float32)
    rgb_img = img[:, :, :3]
    segments = quickshift(img_ndvi, kernel_size=3, convert2lab=False, max_dist=6, ratio=0.5).astype('int32')
    print("Quickshift number of segments: %d" % len(np.unique(segments)))

    # Plot Segments
    if plot_segments:
        fig, ax = plt.subplots(1, 2, figsize=(5, 10))

        # Original Pixels
        ax[0].imshow(rgb_img)
        ax[0].set_title("Original Pixels")
        ax[0].set_xticks([])
        ax[0].set_yticks([])
        ax[0].set_xticklabels([])
        ax[0].set_yticklabels([])
        ax[0].tick_params(axis='both', which='both', length=0)

        # Quickshift Segments
        ax[1].imshow(color.label2rgb(segments, rgb_img, bg_label=0))
        ax[1].set_title("Quickshift Segments")
        ax[1].set_xticks([])
        ax[1].set_yticks([])
        ax[1].set_xticklabels([])
        ax[1].set_yticklabels([])
        ax[1].tick_params(axis='both', which='both', length=0)

        if plot_path:
            plt.savefig(plot_path)
        plt.show()

    # Convert segments to vector features
    polys = []
    for shp, value in tqdm(shapes(segments, transform=affine), desc="Converting segments to vector features"):
        polys.append(shp)

    # Compute mean NDVI for each segment
    mean_ndvi_vals = []
    for shp in tqdm(polys, desc="Computing mean NDVI values"):
        mask = rasterio.features.geometry_mask([shp], transform=affine, invert=True, out_shape=ndvi.shape)
        mean_ndvi_vals.append(ndvi[mask].mean())

    mean_ndvi_vals = np.array(mean_ndvi_vals).reshape(-1, 1)

    # Apply k-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit(mean_ndvi_vals)
    labels = kmeans.labels_

    # Create GeoDataFrame with segments and their cluster labels
    geom = [shape(i) for i in polys]
    gdf = gpd.GeoDataFrame({'geometry': geom, 'cluster': labels}, crs=sr)

    # Determine which cluster corresponds to 'tree' based on NDVI values
    cluster_mean_ndvi = [mean_ndvi_vals[labels == i].mean() for i in range(n_clusters)]
    tree_cluster_idx = np.argmax(cluster_mean_ndvi)

    # Test
    print("Cluster mean NDVI values:", cluster_mean_ndvi)
    print("Index of tree cluster:", tree_cluster_idx)

    # Assign class labels based on the cluster with higher NDVI being 'tree'
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

    return dissolved_gdf


def plot_binary_gdf(dissolved_gdf, filepath=None, save_png_file=False):
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


def multipolygons_to_polygons(dissolved_gdf):
    """
    Converts a GeoDataFrame containing MultiPolygons into individual Polygon geometries.

    Parameters:
    - dissolved_gdf (GeoDataFrame): The GeoDataFrame containing MultiPolygon geometries.

    Returns:
    - GeoDataFrame: A new GeoDataFrame with individual Polygon geometries.
    """
    polygons = []
    classes = []
    for idx, row in dissolved_gdf.iterrows():
        if isinstance(row.geometry, MultiPolygon):
            for poly in row.geometry.geoms:
                polygons.append(poly)
                classes.append(row['class'])
        else:
            polygons.append(row.geometry)
            classes.append(row['class'])
    return gpd.GeoDataFrame({'geometry': polygons, 'class': classes}, crs=dissolved_gdf.crs)


def classless_multipolygons_to_polygons(gdf):
    """
    Converts a GeoDataFrame containing MultiPolygons into individual Polygon geometries without class labels.

    Parameters:
    - gdf (GeoDataFrame): The GeoDataFrame containing MultiPolygon geometries.

    Returns:
    - GeoDataFrame: A new GeoDataFrame with individual Polygon geometries without class labels.
    """
    polygons = []
    for idx, row in gdf.iterrows():
        if isinstance(row.geometry, MultiPolygon):
            for poly in row.geometry.geoms:
                polygons.append(poly)
        else:
            polygons.append(row.geometry)
    return gpd.GeoDataFrame({'geometry': polygons}, crs=gdf.crs)


def calculate_area(gdf):
    """
    Calculates the area in square feet and acres for each polygon in the GeoDataFrame.

    Parameters:
    - gdf (GeoDataFrame): The GeoDataFrame containing Polygon geometries.

    Returns:
    - GeoDataFrame: The input GeoDataFrame with added columns for area in square feet and acres.
    """
    gdf['area_feet'] = gdf.geometry.area
    gdf['area_acres'] = gdf['area_feet'] / 43560
    return gdf


def bin_plot(gdf, bins, labels, title, filepath=None, save_png_file=False):
    """
    Bins the areas of polygons in the GeoDataFrame and plots them.

    Parameters:
    - gdf (GeoDataFrame): The GeoDataFrame containing Polygon geometries.
    - bins (list): A list of bin edges for categorizing the area sizes.
    - labels (list): A list of labels for the bins.
    - title (str): The title of the plot.
    - filepath (str): Path to save the plot (optional).
    - save_png_file (bool): Whether to save the plot as a PNG file (default is False).
    """
    gdf['bin'] = pd.cut(gdf['area_acres'], bins=bins, labels=labels, right=False)
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))

    # Remove axis labels, ticks, and tick labels
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.tick_params(axis='both', which='both', length=0)

    plot = gdf.plot(column='bin', ax=ax, legend=True, categorical=True, legend_kwds={'title': 'Size Category'})
    ax.set_title(title)
    plt.tight_layout()

    if save_png_file:
        plt.savefig(filepath)
    
    plt.show()


def plot_gdf(gdf, title, filepath=None, save_png_file=False):
    """
    Plots a GeoDataFrame with a specified title.

    Parameters:
    - gdf (GeoDataFrame): The GeoDataFrame to plot.
    - title (str): The title of the plot.
    - filepath (str): Path to save the plot (optional).
    - save_png_file (bool): Whether to save the plot as a PNG file (default is False).
    """
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


def get_bounds_gdf(geotiff_path):
    """
    Generates a GeoDataFrame representing the bounding box of a GeoTIFF image.

    Parameters:
    - geotiff_path (str): Path to the GeoTIFF image.

    Returns:
    - GeoDataFrame: A GeoDataFrame containing a single polygon representing the bounding box.
    """
    tile = rasterio.open(geotiff_path)
    bounds = tile.bounds
    minx, miny, maxx, maxy = bounds
    bounds_poly = Polygon([(minx, miny), (minx, maxy), (maxx, maxy), (maxx, miny)])
    gdf = gpd.GeoDataFrame(geometry=[bounds_poly], crs=tile.crs)
    return gdf


def apply_buffer(canopy_gdf, bounds_gdf, buffer_size=5):
    """
    Creates two GeoDataFrames: one for buffered canopy polygons and one for open space polygons.

    Parameters:
    - canopy_gdf (GeoDataFrame): GeoDataFrame containing canopy polygons.
    - bounds_gdf (GeoDataFrame): GeoDataFrame containing the bounds to clip the buffered canopy polygons.
    - buffer_size (int): The size of the buffer to apply to the canopy polygons (default is 5 feet).

    Returns:
    - buffered_gdf (GeoDataFrame): GeoDataFrame containing buffered canopy polygons.
    - openspace_gdf (GeoDataFrame): GeoDataFrame containing open space polygons.
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
