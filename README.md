# treebeard

[![DOI](https://zenodo.org/badge/783989380.svg)](https://zenodo.org/doi/10.5281/zenodo.11107001)

TreeBeard is an open-source GIS plugin designed to automate the classification and quantification of land cover within forested regions using advanced geospatial analysis. This tool leverages high-resolution aerial photography and LiDAR data to facilitate the detailed mapping of tree clusters and open spaces, offering invaluable insights for forestry management, ecological assessments, and environmental planning.ymamb

## How to Run

### Important Note Regarding PDAL

This process requires PDAL (Point Data Abstraction Library) to be installed on the environment. This requires some extra steps beyond normal library installation:

* Install Visual Studio Build Tools:

* https://visualstudio.microsoft.com/visual-cpp-build-tools/

* run pip install pdal

* It may also be necessary to install cmake build tools from here:

* https://cmake.org/download/

(Still working on a solution for MacOS)

### Set up Environment (First Time)
```
conda activate base
conda install -c conda-forge mamba
mamba env create -f environment.yml
conda activate treebeard
```

### Update Environment
```
conda activate treebeard
mamba env update -f environment.yml
```

### Install LASTools

Install LASTools at [https://rapidlasso.de/downloads/](https://rapidlasso.de/downloads/)  
(Note: With Windows/Linux support only)