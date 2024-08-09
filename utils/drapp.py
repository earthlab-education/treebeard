import os
import requests
import urllib.parse
import zipfile

import plotly.express as px
import plotly.graph_objects as go
import geopandas as gpd
import rasterio
from rasterio.merge import merge
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from rasterio.mask import mask
from shapely.geometry import box


def get_filename_from_url(url):
    """
    Extracts and constructs a filename from the provided URL based on query parameters.

    Parameters:
    url (str): The URL containing query parameters.

    Returns:
    str: The constructed filename based on 'outputFormat' and 'typeName' parameters.
    None: If the required parameters are not found in the URL.
    """
    parsed_url = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed_url.query)
    output_format = params.get('outputFormat', [''])[0]
    type_name = params.get('typeName', [''])[0]

    if output_format and type_name:
        format = output_format.lower().split('-')[-1]
        name = type_name.split(':')[-1]
        filename = f"{name}.{format}"
        return filename
    return None


def extract_zip(target_dir, zip_filename, resp):
    """
    Extracts the contents of a ZIP file from an HTTP response into a target directory.

    Parameters:
    target_dir (str): The directory where the ZIP file contents will be extracted.
    zip_filename (str): The name of the ZIP file.
    resp (requests.Response): The HTTP response containing the ZIP file content.
    """
    zip_path = os.path.join(target_dir, zip_filename)
    with open(zip_path, 'wb') as f:
        f.write(resp.content)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(target_dir)


def download_files(localpath, urls):
    """
    Downloads files from a list of URLs and saves them to a specified local directory.

    Parameters:
    localpath (str): The directory where the files will be saved.
    urls (list): A list of URLs to download the files from.

    Returns:
    list: A list of paths to the downloaded files.
    """
    paths = []
    for url in urls:
        filename = os.path.basename(url)
        path = os.path.join(localpath, filename)
        paths.append(path)
        if not os.path.exists(path):
            resp = requests.get(url)
            with open(path, 'wb') as f:
                f.write(resp.content)
    return paths


def save_shapefile(local_path: str, url=None):
    """
    Saves a shapefile from a specified URL to a local directory.

    Parameters:
    local_path (str): The directory where the shapefile will be saved.
    url (str, optional): The URL to download the shapefile from. Defaults to DRAPP Tile Scheme URL.

    Returns:
    str: The path to the saved shapefile.
    """
    if not os.path.exists(local_path):
        os.makedirs(local_path)

    if not url:
        drapp_url = (
            'https://gisdata.drcog.org:8443'
            '/geoserver/DRCOGPUB/ows?'
            'service=WFS&version=1.0.0&'
            'request=GetFeature&'
            'typeName=DRCOGPUB:drapp_tile_scheme_2020'
            '&outputFormat=SHAPE-ZIP'
        )
        url = drapp_url
    zipfilepath = os.path.join(local_path, get_filename_from_url(url))
    shapefilepath = zipfilepath.replace('.zip', '.shp')

    if not os.path.exists(shapefilepath):
        resp = requests.get(url)
        extract_zip(local_path, zipfilepath, resp)

    return shapefilepath


def save_tiles(localpath, tilenames: list, tile_base_url=None):
    """
    Downloads and saves DRAPP tiles to a specified local directory.

    Parameters:
    localpath (str): The directory where the tiles will be saved.
    tilenames (list): A list of tile names to download.
    tile_base_url (str, optional): The base URL for the tile files. Defaults to DRAPP archive URL.

    Returns:
    list: A list of paths to the downloaded tile files.
    """
    os.makedirs(localpath, exist_ok=True)
    if not tile_base_url:
        tile_base_url = 'https://drapparchive.s3.amazonaws.com/2020/'
    tile_urls = [f'{tile_base_url}{tile}.tif' for tile in tilenames]

    tile_paths = download_files(localpath, tile_urls)
    return tile_paths


def plot_aoi_bbox(aoi_gdf, bbox_aoi_gdf, drapp_aoi_gdf):
    """
    Creates a map visualizing the Area of Interest (AOI), bounding box, and DRAPP tiles.

    Parameters:
    aoi_gdf (GeoDataFrame): GeoDataFrame containing the Area of Interest (AOI).
    bbox_aoi_gdf (GeoDataFrame): GeoDataFrame containing the bounding box of the AOI.
    drapp_aoi_gdf (GeoDataFrame): GeoDataFrame containing DRAPP tiles intersecting the AOI.

    Returns:
    plotly.graph_objects.Figure: A Plotly Mapbox figure showing the AOI, bounding box, and DRAPP tiles.
    """
    # Add label to AOI GeoDataFrame
    aoi_gdf['label'] = 'Area of Interest'

    # Create a choropleth mapbox plot for AOI
    fig = px.choropleth_mapbox(
        aoi_gdf, 
        geojson=aoi_gdf.geometry, 
        locations=aoi_gdf.index, 
        color='label', 
        color_discrete_sequence=["red"],
        mapbox_style="open-street-map",
        center={"lat": aoi_gdf.centroid.y.mean(), "lon": aoi_gdf.centroid.x.mean()}, 
        zoom=11
    )

    # Add DRAPP tiles to the map
    for idx, row in drapp_aoi_gdf.iterrows():
        tile_info = f"{row['tile']} {row['photo_date']}"
        fig.add_trace(go.Scattermapbox(
            lon=[coord[0] for coord in row.geometry.exterior.coords],
            lat=[coord[1] for coord in row.geometry.exterior.coords],
            mode='lines',
            line=dict(width=2, color='blue'),
            name=tile_info
        ))

    # Add bounding box of AOI to the map
    for idx, row in bbox_aoi_gdf.iterrows():
        fig.add_trace(go.Scattermapbox(
            lon=[coord[0] for coord in row.geometry.exterior.coords],
            lat=[coord[1] for coord in row.geometry.exterior.coords],
            mode='lines',
            line=dict(width=2, color='black'),
            name='Bounding Box'
        ))

    return fig


def get_utm_zone_from_bbox(bbox):
    """
    Calculate the UTM zone for a given bounding box.

    Parameters:
    bbox (tuple): A bounding box tuple in the form (minx, miny, maxx, maxy).

    Returns:
    int: The UTM zone number.
    str: The UTM zone EPSG code.
    """
    # Create a bounding box geometry
    bbox_geom = box(*bbox)
    
    # Get the centroid of the bounding box
    centroid = bbox_geom.centroid

    # Extract latitude and longitude from the centroid
    lon = centroid.x
    lat = centroid.y

    # Calculate the UTM zone
    utm_zone = int((lon + 180) / 6) + 1

    # Determine the UTM hemisphere
    if lat >= 0:
        hemisphere = 'N'
    else:
        hemisphere = 'S'

    # EPSG code for the UTM zone
    epsg_code = f"EPSG:326{utm_zone:02d}" if hemisphere == 'N' else f"EPSG:327{utm_zone:02d}"

    return utm_zone, epsg_code


def crop_geotiff(merged_tile_path: str,
                 bbox_aoi_gdf: gpd.GeoDataFrame,
                 crop_output_path: str):
    """
    Crops a merged GeoTIFF file based on a bounding box GeoDataFrame.

    Parameters:
    merged_tile_path (str): The path to the merged GeoTIFF file.
    bbox_aoi_gdf (GeoDataFrame): GeoDataFrame containing the bounding box geometry.
    crop_output_path (str): The path to save the cropped GeoTIFF file.

    Returns:
    str: The path to the saved cropped GeoTIFF file.
    """
    # Open the merged GeoTIFF file
    with rasterio.open(merged_tile_path) as src:
        # Ensure the GeoDataFrame's CRS matches the raster's CRS
        if bbox_aoi_gdf.crs != src.crs:
            bbox_aoi_gdf = bbox_aoi_gdf.to_crs(src.crs)

        # Create a mask for cropping
        geom = [bbox_aoi_gdf.geometry.unary_union]  # Combine all geometries in the GeoDataFrame
        out_image, out_transform = mask(src, geom, crop=True)

        # Update the metadata for the cropped raster
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })

    # Save the cropped GeoTIFF file
    with rasterio.open(crop_output_path, "w", **out_meta) as dest:
        dest.write(out_image)

    return crop_output_path


def merge_tiles(drapp_tilepaths: list,
                merge_path: str):
    """
    Merges multiple DRAPP tiles into a single GeoTIFF file.

    Parameters:
    drapp_tilepaths (list): A list of paths to the DRAPP tiles to be merged.
    merge_path (str): The path to save the merged GeoTIFF file.

    Returns:
    str: The path to the saved merged GeoTIFF file.
    """
    # Open all the files
    src_files_to_mosaic = [rasterio.open(path) for path in drapp_tilepaths]
    mosaic, out_trans = merge(src_files_to_mosaic)

    # Save the merged tile as a GeoTIFF
    out_meta = src_files_to_mosaic[0].meta.copy()
    out_meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_trans,
        "count": mosaic.shape[0]
    })

    output_path = merge_path

    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(mosaic)

    # Close all opened files
    for src in src_files_to_mosaic:
        src.close()

    return output_path


def plot_rgb_image(tile_path: str,
                   drapp_aoi_gdf: gpd.GeoDataFrame,
                   title_prefix: str = "RGB Image:",
                   save_png_file=False):
    """
    Plots an RGB image from a GeoTIFF file and optionally saves it as a PNG.

    Parameters:
    tile_path (str): The path to the GeoTIFF file.
    drapp_aoi_gdf (GeoDataFrame): GeoDataFrame containing DRAPP tiles intersecting the AOI.
    title_prefix (str): A prefix for the plot title.
    save_png_file (bool): Whether to save the plot as a PNG file.

    Returns:
    None
    """
    # Open the merged GeoTIFF file
    with rasterio.open(tile_path) as src:
        mosaic = src.read()
        red = mosaic[0]
        green = mosaic[1]
        blue = mosaic[2]
        rgb = np.dstack((red, green, blue))

    # Create the plot
    fig, ax = plt.subplots()
    ax.imshow(rgb)

    # Remove axis labels, ticks, and tick labels
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.tick_params(axis='both', which='both', length=0)

    # Get counts and unique values
    tiles_count = len(drapp_aoi_gdf['tile'].unique())
    photo_dates_count = len(drapp_aoi_gdf['photo_date'].unique())
    photo_date = (pd.to_datetime(drapp_aoi_gdf['photo_date'])
                    .dt.date.unique()[0]
                    .strftime('%Y-%m-%d'))

    # Determine the title
    if tiles_count > 1:
        if photo_dates_count > 1:
            title = f'{title_prefix} DRAPP Tiles (Multiple)'
        elif photo_dates_count == 1:
            title = f'{title_prefix} DRAPP Tiles (Multiple) ({photo_date})'
    elif tiles_count == 1:
        tile_name = drapp_aoi_gdf['tile'].unique()[0]
        title = f'{title_prefix} DRAPP Tile {tile_name} ({photo_date})'

    ax.set_title(title)

    # Save PNG File
    if save_png_file:
        output_path = tile_path.replace('.tif', '.png')
        plt.savefig(output_path)
