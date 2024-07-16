import os
import requests
import urllib.parse
import zipfile


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


def save_drapp_tiles(localpath, tilenames: list):
    os.makedirs(localpath, exist_ok=True)
    tile_base_url = 'https://drapparchive.s3.amazonaws.com/2020/'
    tile_urls = [f'{tile_base_url}{tile}.tif' for tile in tilenames]
    
    tile_paths = download_files(localpath, tile_urls)
    return tile_paths