# LT SWAT Land Use Data Processing

This repository contains Python scripts and tools for processing geospatial land use data to prepare raster inputs for the SWAT (Soil and Water Assessment Tool) model, specifically tailored for [Lithuania's river modeling system](https://srees.sggw.edu.pl/article/view/9790/8738). The workflow includes reading geospatial data, rasterizing vector layers, merging rasters, generating statistics, comparing with previous land use maps, and creating a final raster and lookup table for model integration.

## Project Overview

- **Created on**: 2024-11-29  
- **Last Modified**: 2025-04-30  
- **Author**: Svajunas Plunge  
- **Email**: svajunas_plunge@sggw.edu.pl  

The scripts process land use data from various sources (e.g., crops, forests, impervious surfaces) and transform them into a raster format compatible with the LT SWAT model. The workflow is modular, with configurable steps controlled by switches in the main script.

### Key Features
1. **Rasterization**: Converts vector data (e.g., GeoPackages, shapefiles) into raster format.
2. **Merging**: Combines multiple raster layers into a single output.
3. **Statistics**: Generates area statistics by SWAT land use codes.
4. **Comparison**: Compares the new land use raster with a previous version.
5. **Final Output**: Produces a final raster (`LUraster.tif`) and a lookup table for SWAT model integration.

## Repository Structure

```
LT-SWAT-LandUse-Processing/
├── docs/                  # Documentation folder (if applicable)
├── Temp/                  # Temporary output folder for intermediate files
├── imperv_process.py     # Preprocesses a raster file representing impervious land (optional).
├── functions.py          # Core functions for data processing
├── settings.py           # Configuration settings (data paths, parameters)
├── main.py               # Main script to execute the workflow
├── lookup.xlsx           # Lookup table mapping global land use codes to SWAT codes
└── README.md             # This file
```


### Lookup Table (`lookup.xlsx`)
The `lookup.xlsx` file contains the mapping between `globalcode` (land use categories from input data) and `SWATCODE` (SWAT model land use codes). This file is used in the statistics generation step to translate raster IDs into meaningful SWAT categories. It includes mappings such as:

- `C_ŽM-1` → `FRSE` (Forest-Evergreen)
- `C_KUK` → `CORN` (Corn)
- `F_1_P` → `PINE` (Pine Forest)
- `G_hd4` → `WATR` (Water)
- `U_URHD` → `URHD` (Urban Residential High Density)

The file has two columns: `globalcode` and `SWATCODE`, with over 300 entries covering various land use types (e.g., crops, forests, wetlands, urban areas).

## Prerequisites

### Software Requirements
- Python 3.8 or higher
- PostgreSQL (for database integration)
- Libraries:
  - `geopandas`
  - `pandas`
  - `numpy`
  - `rasterio`
  - `shapely`
  - `matplotlib`
  - `psycopg2`

Install dependencies using pip:
```bash
pip install geopandas pandas numpy rasterio shapely matplotlib psycopg2-binary
```

### Data Requirements
- Geospatial data files (e.g., `.gpkg`, `.tif`, `.gdb`) as specified in `settings.py`.
- A previous land use raster for comparison (e.g., `LUraster_bck.tif`).
- The `lookup.xlsx` file (included in the repository) for mapping land use codes to SWAT codes.
- Access to a PostgreSQL database (optional, for lookup table storage).

## Usage

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/biopsichas/lu_update.git
   ```
2. **Configure Settings**:

- Edit `settings.py` to specify:
    - Paths to input data (data_source).
    - Output directory (cropped_path).
    - Database connection parameters (db_params).
    - Resolution and bounding box (if clipping to a smaller area).
- Ensure `lookup.xlsx` is in the repository root directory (already included).
3. **Run the Script**:

Execute `main.py` to process the data:

   ```bash
   python main.py
   ```
4. Outputs:

- Intermediate rasters and statistics are saved in the `Temp/` folder.
- Final outputs:
  - `LUraster.tif`: Final land use raster for SWAT.
  - `landuse_swat_raster_lookup.csv`: Lookup table for SWAT codes.

5. **Integrate with SWAT**:

- Manually place `LUraster.tif` in the SWAT project folder (e.g., `Projects\Setup_2020_common\Data\Rasters\`).
- Update the SWAT database with `landuse_swat_raster_lookup.csv` if applicable.

## Workflow Steps

1. **Rasterize Layers**:
   - Reads vector data (e.g., GeoPackages) and rasterizes them into individual rasters.
   - Each raster represents a specific land use category (e.g., crops, forests, urban areas).
2. **Merge Rasters**:
   - Combines individual rasters into a single `merged_output.tif`.
3. **Create Statistics**:
   - Generates area summaries and plots by SWAT code using `lookup.xlsx` to map IDs to SWAT codes.
4. **Compare to Previous**:
   - Analyzes differences between the new land use raster and a previous version (e.g., `LUraster_bck.tif`).
5. **Final Raster**:
   - Produces the final land use raster (`LUraster.tif`) and a lookup table for SWAT model integration.
   
Each step can be toggled on/off in `main.py`.

## Example configuration in `settings.py`

```python
projectDir = "G:\\LIFE_AAA\\swat_lt\\"
dataDir = projectDir + "Data\\"
cropped_path = "Temp\\"
resolution = 5  # Grid size in meters
bbox = None  # Full extent; set coordinates for a smaller area if needed

data_source = {
    "crops": ("KODAS", "C", "Crops2024", "path/to/Crops2024.gpkg"),
    "imperv2024": ("Cat", "U", "imperv2024", "path/to/imperv2024.gpkg"),
    # Add other layers as needed
}

```

## Acknowledgments

This work was carried out within the LIFE22-IPE-LT-LIFE-SIP-Vanduo project (Integratedwater management in Lithuania, ref: LIFE22-IPE-LT-LIFE-SIP-Vanduo/101104645,cinea.ec.europa.eu), funded by the European Union LIFE program under the grant agreementNo 101104645.  


   
