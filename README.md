# treebeard

[![DOI](https://zenodo.org/badge/783989380.svg)](https://zenodo.org/doi/10.5281/zenodo.11107001)

Treebeard is a project for **identifying canopy gaps/tree gaps for foresters**, developed during Earth Data Analytics Professional Graduate Certificate Program at CU Boulder by these students: Ed Chan, Chris Griego, and Peter Kobylarz.

## Quick Links
- [Project Background](#project-background)
- [Objectives](#objectives)
- [Data Source](#data-source)
- [Project Workflow](#project-workflow)
- [Results](#results)
- [How to Run Jupyter Notebooks](#how-to-run-jupyter-notebooks)
- [How to Run the QGIS Plug-in](#how-to-run-the-qgis-plug-in)
- [Appendix](#appendix)
    - [Pre-requisites](#pre-requisites)
    - [Setup Instructions](#setup-instructions)
        - [Set up Environment (First Time)](#set-up-environment-first-time)
        - [Update Environment](#update-environment)
    - [Image Segmentation Method](#image-segmentation-method)
    - [LIDAR Processing Method](#lidar-processing-method)


## Project Background
The Watershed Center is interested in identifying canopy gaps and binning them by size (1/8 acre, 1/4 acre, 1/2 acre, and 1+ acre). 

To quote the forester Eric Frederick:
> Forest structural diversity is a key component of forest ecosystem health, as forests that contain structural heterogeneity are critical for providing wildlife habitat and can be more resilient to natural disturbances. Being able to quantify forest structural heterogeneity is important to be able to assess the need for potential management actions, and it allows us to ensure that our forest management projects are creating structural heterogeneity rather than homogeneity. This tool will allow us to better determine the need for canopy gaps in project areas, and it will allow us to more accurately pinpoint beneficial locations for creating canopy gaps of various sizes when implementing projects.

## Objectives
1. Develop image segmentation method
2. Develop LIDAR processing method
3. Develop QGIS plug-in

## Data Source
- Shape files representing study areas from the Watershed Center
    - It's already part of the repo at `assets/` which you get from cloning this repository
    - You can prepare your own study area shapefiles and specify them as inputs:
        - In `treebeard_image_segmentation.ipynb`, update these variables: `STUDY_AREA` and `AOI_SHAPEFILES`.
        - In `treebeard_lidar.ipynb`, make sure to include the column called `Proj_ID` that contains values of study area names.
- [Aerial Data: "Denver Regional Aerial Photography Project (DRAPP)", Denver Regional Counsel of Governance, 2020.](https://data.drcog.org/dataset/denver-regional-aerial-photography-project-tiles-2020) 
- [LIDAR Data: "DRCOG LIDAR QL2 INDEX IN CO SP NORTH 2020", Denver Regional Counsel of Governance.](https://data.drcog.org/dataset/lidar-ql2-index-in-co-sp-north-2020)

Notes: 
- Beware the notebooks will download these aerial imagery tiles and LIDAR tiles for you. Please review the download destinations accordingly for your needs.
- This tool should work with other imagery and LIDAR data sources. You will need to adjust the code to point to the download URLs for index layers and tile downloads.

## Output Folder Location
This workflow uses the [EarthyPy libary](https://github.com/earthlab/earthpy). This library has a default data directory, and the sub directories set up used in the code have the EarthPy directory as parent. You can change your parent directory by adjusting the "data_dir" path variable near the beginning of the notebooks. The default folder path is:

**Windows**
```plaintext
C:\Users\[username]\earth-analytics\data
```

**MacOS**
```
/Users/[username]/earth-analytics/data
```

## Project Workflow

![Treebeard Project Workflow](images/project_workflow.png)

## Results

The results from image segmentation and LIDAR processing yield similar outcomes except the highlighted areas:

![Compare Results](images/compare_results.png)

## How to Run Jupyter Notebooks
1. [Set up the environment](#set-up-environment-first-time) / [Update environment](#update-environment)
2. Run `treebeard_image_segmentation.ipynb`
3. Run `treebeard_lidar.ipynb`

## How to Run the QGIS Plug-in
Please refer to the README file at [`qgis_build/treebeard/README.md`](https://github.com/earthlab-education/treebeard/blob/main/qgis_build/treebeard/README.md).

## Appendix

### Pre-requisites
- Install [Conda](https://conda.io/projects/conda/en/latest/user-guide/getting-started.html)

### Setup Instructions

#### Set up Environment (First Time)
```
conda activate base
conda install -c conda-forge mamba
mamba env create -f environment.yml
conda activate treebeard
```

#### Update Environment
```
conda activate treebeard
mamba env update -f environment.yml
```

### Image Segmentation Method

Here are illustrations of image segmentation:

![Image Segmentation 01](images/image_segmentation_01.png)
![Image Segmentation 02](images/image_segmentation_02.png)
![Image Segmentation 03](images/image_segmentation_03.png)
![Buffer Area Bin](images/buffer_area_bin.png)

### LIDAR Processing Method

Here are illustrations of LIDAR processing:
![LIDAR Processing 01](images/LIDAR_01.png)
![LIDAR Processing 02](images/LIDAR_02.png)
