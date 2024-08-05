# Utility methods used in processing LIDAR .las files into canopy gaps
import numpy as np
import os
import sys

import rioxarray
import rasterio
import geopandas as gpd
from shapely.geometry import shape
from scipy.ndimage import binary_opening, binary_closing
from shapely.ops import unary_union
import whitebox

# Process LAS files to canopy using Whitebox
def convert_las_to_tif(input_las, output_tif, return_type):
    """
    Converts a LAS file to a GeoTIFF using WhiteboxTools, based on the specified return type,
    processes it in a temporary file, sets the CRS to the specified EPSG code, and saves it to the output path.

    Parameters
    ----------
    input_las : str
        Path to the input LAS file.
    output_tif : str
        Path to save the output GeoTIFF file.
    return_type : str
        Type of returns to process. Must be either 'first' for first returns or 'ground' for ground returns.
    """
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')

    wbt = whitebox.WhiteboxTools()

    # Process LAS file to TIFF based on return type
    if return_type == "first":
        wbt.lidar_idw_interpolation(
            i=input_las,
            output=output_tif,
            parameter="elevation",
            returns="first",
            resolution=1.0,
            radius=3.0
        )
    elif return_type == "ground":
        wbt.lidar_idw_interpolation(
            i=input_las,
            output=output_tif,
            parameter="elevation",
            returns="ground",
            resolution=1.0,
            radius=3.0
        )
    else:
        raise ValueError("Invalid return_type. Use 'first' or 'ground'.")

    
# Function to apply morphological operations on a rioxarray DataArray
def clean_raster_rioxarray(raster_xarray, operation='opening', structure_size=3):
    """
    Cleans up "noise" in the canopy/gap raster with opening/closing morphological operations

    Parameters
    ----------
    raster_xarray : xarray.DataArray
        The input raster data as an xarray DataArray.
    operation : str, optional
        The morphological operation to apply. Must be either 'opening' or 'closing'. Default is 'opening'.
    structure_size : int, optional
        The size of the structure element for the morphological operation. Default is 3.

    Returns
    -------
    cleaned_raster_xarray : xarray.DataArray
        The cleaned raster data as an xarray DataArray.

    Raises
    ------
    ValueError
        If the operation is not 'opening' or 'closing'.

    Examples
    --------
    >>> cleaned_raster = clean_raster_rioxarray(raster_xarray, operation='opening', structure_size=3)
    """
    # Extract the numpy array from the xarray DataArray
    raster_data = raster_xarray.values

    # Ensure the raster_data is 2D (in case it's a single-band raster with an extra dimension)
    if raster_data.ndim == 3 and raster_data.shape[0] == 1:
        raster_data = raster_data[0, :, :]
    
    # Convert to binary (tree canopy is represented by 1, no canopy by 0)
    binary_raster = raster_data == 1

    # Define the structure for the morphological operation
    structure = np.ones((structure_size, structure_size), dtype=int)

    # Apply the chosen morphological operation
    if operation == 'opening':
        cleaned_raster = binary_opening(binary_raster, structure=structure)
    elif operation == 'closing':
        cleaned_raster = binary_closing(binary_raster, structure=structure)
    else:
        raise ValueError("Operation must be 'opening' or 'closing'")

    # Convert back to the original values (1 for canopy, 0 for no canopy)
    raster_data_cleaned = np.where(cleaned_raster, 1, 0)

    # Add back the extra dimension if the original data had it
    if raster_xarray.values.ndim == 3:
        raster_data_cleaned = np.expand_dims(raster_data_cleaned, axis=0)

    # Create a new xarray DataArray with the cleaned data, copying metadata from the original
    cleaned_raster_xarray = raster_xarray.copy(data=raster_data_cleaned)

    return cleaned_raster_xarray


def export_lidar_canopy_tif(lidar_cleaned, output_path):
    """
    Exports the cleaned lidar canopy data to a GeoTIFF file and generates a GeoDataFrame of canopy polygons.
    
    Parameters:
    - lidar_cleaned: xarray.DataArray containing the cleaned lidar canopy data.
    - output_path: str, the path where the GeoTIFF file will be saved.
    
    Returns:
    - canopy_gdf: GeoDataFrame containing the canopy polygons.
    """
    # Export the lidar canopy tif to the specified path
    lidar_cleaned = lidar_cleaned.where(lidar_cleaned != 1.7976931348623157e+308, np.nan)
    lidar_cleaned.rio.to_raster(output_path, overwrite=True)
    
    # Load the TIF file using rioxarray
    binary_mask = lidar_cleaned.squeeze()  # Assuming the data is in the first band
    
    # Create a mask where cell values are 1
    mask = binary_mask == 1
    
    # Get the affine transform from the raster data
    transform = binary_mask.rio.transform()
    
    # Extract shapes (polygons) from the binary mask
    shapes = rasterio.features.shapes(mask.astype(np.int16).values, transform=transform)
    polygons = [shape(geom) for geom, value in shapes if value == 1]
    
    # Create a GeoDataFrame from the polygons
    canopy_gdf = gpd.GeoDataFrame({'geometry': polygons})
    
    return canopy_gdf

# Example usage:
# lidar_cleaned = ... # Load your xarray.DataArray here
# output_path = "../notebooks/lidar_clean_canopy.tif"
# canopy_gdf = export_lidar_canopy_tif(lidar_cleaned, output_path)

# Method to process canopy gaps.
def process_canopy_areas(canopy_gdf, study_area, buffer_distance=5):
    """
    Processes canopy areas by buffering, dissolving, clipping, and exploding the geometries.
    Adds acreage and size category columns.

    Parameters
    ----------
    canopy_gdf : gpd.GeoDataFrame
        GeoDataFrame representing canopy areas.
    study_area : gpd.GeoDataFrame
        GeoDataFrame representing the boundary within which to clip the canopy areas.
    buffer_distance : float, optional
        The distance to buffer the canopy geometries. Default is 5 units.

    Returns
    -------
    clipped_buffer : gpd.GeoDataFrame
        GeoDataFrame with the buffered and clipped canopy areas.
    exploded_gap_gdf : gpd.GeoDataFrame
        GeoDataFrame with exploded geometries representing non-tree canopy areas, including acreage and size category.
    """
    
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

    return clipped_buffer, exploded_gap_gdf