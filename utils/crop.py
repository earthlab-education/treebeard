import os
import requests
import urllib.parse
import zipfile
import plotly.express as px
import plotly.graph_objects as go
import geopandas as gpd
from shapely.geometry import MultiPolygon


def check_contiguity(gdf: gpd.GeoDataFrame) -> bool:
    """
    Check if geometries in a GeoDataFrame are contiguous.
    
    Parameters:
    gdf (GeoDataFrame): GeoDataFrame to check for contiguity.

    Returns:
    bool: True if all geometries are contiguous, False otherwise.
    """
    gdf = gdf.dissolve()
    is_multipolygon = gdf.geometry.apply(
        lambda geom: isinstance(geom, MultiPolygon)).all()
    is_contiguous = not is_multipolygon
    return is_contiguous


def get_filename_from_url(url):
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
    zip_path = os.path.join(target_dir, zip_filename)
    with open(zip_path, 'wb') as f:
        f.write(resp.content)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(target_dir)


def download_files(localpath, urls):
    paths = []
    for url in urls:
        filename = os.path.basename(url)
        path = os.path.join(localpath, filename)
        paths.append(path)
        if not os.path.exists(path):
            print(f"Downloading {url}...")
            resp = requests.get(url)
            with open(path, 'wb') as f:
                f.write(resp.content)
        else:
            print(f"File {filename} already downloaded.")
    return paths


def save_drapp_shapefile(local_path: str, url=None):
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


def save_drapp_tiles(localpath, tilenames: list, tile_base_url=None):
    os.makedirs(localpath, exist_ok=True)
    if not tile_base_url:
        tile_base_url = 'https://drapparchive.s3.amazonaws.com/2020/'
    tile_urls = [f'{tile_base_url}{tile}.tif' for tile in tilenames]
    
    tile_paths = download_files(localpath, tile_urls)
    return tile_paths


def plot_aoi_bbox_drapp(aoi_gdf, bbox_aoi_gdf, drapp_aoi_gdf):
    """
    Generate a Plotly mapbox plot with AOI, BBOX, and DRAPP tiles.

    Parameters:
    aoi_gdf (GeoDataFrame): GeoDataFrame containing the AOI geometry.
    bbox_aoi_gdf (GeoDataFrame): GeoDataFrame containing the bounding box geometry.
    drapp_aoi_gdf (GeoDataFrame): GeoDataFrame containing the DRAPP tile geometries along with photo_date and tile information.

    Returns:
    fig (Figure): Plotly figure with the map and overlays.
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