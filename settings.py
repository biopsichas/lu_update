# Data paths and settings
mylookup = "lookup.xlsx"  # Path to the lookup table

projectDir = "G:\\LIFE_AAA\\swat_lt\\"
dataDir = projectDir + "Data\\"  # Data directory
gdb_path = dataDir + "LandUse\\landuse.gdb"  # Path Landuse to the geodatabase
# Path to the output directory (where the results will be stored)
cropped_path = "Temp\\"

# Data source settings, layer names, and land use column, and the letter to identify codes. The sequence is important!!!
# Later dataset is used if NA values are present in the earlier datasets.
data_source = {
    "crops": (
    "KODAS", "C", "Crops2024", "G:\\LIFE_AAA\\swat_lt\\Data\\LandUse\\Landuse_update\\2024\\inputs\\Crops2024.gpkg"),
    "forest_wetland": (
    "augaviete", "W", "forest2022", "G:\\LIFE_AAA\\swat_lt\\Data\LandUse\\Landuse_update\\inputs\\forest2022.gpkg"),
    "forest": ("VMR", "F", "Misko_sklypai",
               "G:\\LIFE_AAA\\swat_lt\\Data\\LandUse\\Landuse_update\\2024\\raw\\forest\\VMT_MKD.gdb"),
    "abandoned": ("A", "A", "abandoned_2024",
                  "G:\\LIFE_AAA\\swat_lt\\Data\\LandUse\\Landuse_update\\2024\\inputs\\abandoned_2024.gpkg"),
    "gdr": (
    "GKODAS", "G", "gdr2024", "G:\\LIFE_AAA\\swat_lt\\Data\\LandUse\\Landuse_update\\2024\\inputs\\gdr2024.gpkg"),
    "imperv2024": (
    "Cat", "U", "imperv2024", "G:\\LIFE_AAA\\swat_lt\\Data\\LandUse\\Landuse_update\\2024\\inputs\\imperv2024.gpkg"),
    "gdr2": (
    "GKODAS", "M", "gdr2024", "G:\\LIFE_AAA\\swat_lt\\Data\\LandUse\\Landuse_update\\2024\\inputs\\gdr2024.gpkg")
}

# Coordinates, if clip is required to test on small area (don't forget to comment out the bbox = None to work)
# xmn, ymn = 475237, 6178256
# xmx, ymx = 486495, 6187595
# bbox = (xmn, ymn, xmx, ymx)
bbox = None  # Set to None to use the full extent

# Resolution of the output raster
resolution = 5  # Grid size

# Define connection parameters
db_params = {
    "dbname": "LTSWAT2020_coarse",
    "user": "postgres",  # Replace with your PostgreSQL username
    "password": "Upelis3600",  # Replace with your PostgreSQL password
    "host": "localhost",  # Replace with your PostgreSQL host (e.g., "127.0.0.1")
    "port": "5444"  # Replace with your PostgreSQL port
}

# Define the previous land use raster path
raster_prv = "G:\\LIFE_AAA\\swat_lt\\Projects\\Setup_2020_common\\Data\\Rasters\\LUraster_bck.tif"
