# treebeard

[![DOI](https://zenodo.org/badge/783989380.svg)](https://zenodo.org/doi/10.5281/zenodo.11107001)

## How to Run

### Set up Environment
```
conda activate base
conda install -c conda-forge mamba
mamba env create -f environment.yml
conda activate treebeard
pip install git+https://github.com/earthlab/earthpy@apppears
```

### Install LASTools

Install LASTools at [https://rapidlasso.de/downloads/](https://rapidlasso.de/downloads/)  
_Note: With Windows/Linux support only_