import sys
from settings import *
import geopandas as gpnd
import pandas as pd
import numpy as np
import time
from shapely.geometry import box
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_bounds
import matplotlib.pyplot as plt
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine, text

def raster_stats(raster_path):
    """
    Count the number of pixels in each category in a raster file.

    Parameters:
    raster_path (str): The path to the file of the raster file.

    Returns:
    pd_values (pandas.DataFrame): A DataFrame with the unique values, their counts, and the area in km^2.
    """
    # Open the raster file and read the image
    with rasterio.Env():
        with rasterio.open(raster_path) as src:
            image = src.read(1)

            transform = src.transform

            # Cell size (resolution)
            cell_width = transform.a  # Pixel width
            cell_height = -transform.e  #

            # Count unique values and their frequencies
            unique, counts = np.unique(image, return_counts=True)

            # Create DataFrame with counts and map them with SWATCODE
            pd_values = pd.DataFrame({
                'ID': unique.astype(int),
                'Count': counts,
                'Area_km2': (counts * cell_width * cell_height) / 1000000  # Convert to km^2 assuming pixel size is 25m x 25m
            })

    return pd_values

def check_crs(gdf):
    """
    Check if the CRS of a GeoDataFrame is EPSG:3346 and convert it if necessary.

    :param gdf: GeoDataFrame to check and potentially reproject.
    :return: GeoDataFrame with CRS set to EPSG:3346.
    """
    # Ensure the GeoDataFrame has a CRS
    if gdf.crs is None:
        print("Warning: GeoDataFrame has no CRS. Assigning EPSG:3346 as default.")
        gdf = gdf.set_crs(epsg=3346)  # Assign EPSG:3346 if CRS is missing
    elif gdf.crs.to_epsg() == 3346:
        print("Coordinates are already in EPSG:3346.")
    else:
        print(f"Converting CRS from {gdf.crs} to EPSG:3346.")
        gdf = gdf.to_crs(epsg=3346)  # Convert to EPSG:3346 if not already
    return gdf

def time_used(start_time):
    """
    Prints the duration of data processing in hours, minutes, and seconds.

    Parameters:
    start_time (float): The starting time in seconds since the epoch, typically
                        obtained using time.time().

    Returns:
    None: The function prints the elapsed time in a formatted string but does not return a value.
    """
    hours, rem = divmod(time.time() - start_time, 3600)
    minutes, seconds = divmod(rem, 60)
    print('Data processing lasted {0} h, {1} m and {2} s!'.format(int(hours), int(minutes), round(seconds, 2)))

def clean_attibutes(gdf, column_name, new_name):
    """
    Function to clean and process attributes of a GeoDataFrame by creating a new attribute
    ('LU') based on the values of an existing column and the provided new name.

    The 'LU' column is created based on specific conditions that vary depending on the
    value of the 'new_name' parameter.

    :param gdf: GeoDataFrame
        The input GeoDataFrame that contains the vector data. This should include both
        geometry and attribute columns.
    :param column_name: str
        The name of the column from which to generate the new 'LU' attribute. The function
        will use this column to construct the 'LU' values based on various conditions.
    :param new_name: str
        A string that defines how the 'LU' attribute will be constructed. It can be:
        - "F": Generates a more complex 'LU' value, with conditional logic.
        - "A": Assigns a fixed value ("A_") to the 'LU' column for all rows.
        - Any other string: The 'LU' column is formed by concatenating `new_name` with values from
          the `column_name` column.

    :return: GeoDataFrame
        The cleaned and processed GeoDataFrame with the newly created 'LU' column and dissolved features.
    """

    # If new_name is "F", create a more complex 'LU' value based on conditions
    if new_name == "F":
        # gdf["LU"] = gdf.apply(
        #     lambda row: f"{new_name}_{row['naudmena']}_{round(row['vyr_medz_r'], 0)}_{row['augaviete']}"
        #     if row['augaviete'] in ['Pa', 'Pan', 'Pb']  # Special case for specific 'augaviete' values
        #     else f"{new_name}_{row['naudmena']}_{round(row['vyr_medz_r'], 0)}", axis=1
        # )
        gdf["LU"] = gdf.apply(
            lambda row: f"{new_name}_{round(row['zkg'], 0)}_{row[column_name]}"
            if row['zkg'] not in [0, 2, 4, 5]
            else None, axis=1
        )
        # gdf["LU"] = new_name + "_" + round(gdf['zkg'], 0).astype(str) + "_" + gdf[column_name]
    elif new_name == "W":
        gdf["LU"] = gdf.apply(
            lambda row: f"{new_name}_{row[column_name]}"
            if row[column_name] in ['Pa', 'Pan', 'Pb']
            else None, axis=1
        )
    elif new_name == "C":
        gdf["LU"] = gdf.apply(
            lambda row: f"{new_name}_{row[column_name]}"
            if row[column_name] not in ["NEP", "TPN"]
            else None, axis=1
        )

    # If new_name is "A", assign a fixed value "A_" to 'LU' for all rows
    elif new_name == "A":
        gdf["LU"] = "A_"

    # If new_name is "G", create a more complex 'LU' value based on conditions
    elif new_name == "G":
        gdf["LU"] = gdf.apply(
            lambda row: f"{new_name}_{row[column_name]}"
            if row[column_name] not in ['pu0', 'pu3']
            else None, axis=1
        )

    # For any other value of new_name, concatenate new_name with the values in column_name
    else:
        gdf["LU"] = new_name + "_" + gdf[column_name]

    # Select only the 'LU' and 'geometry' columns for further processing
    gdf = gdf[["LU", "geometry"]]

    # Remove rows where 'LU' is None or NaN
    gdf = gdf.dropna(subset=['LU'])

    # Return the cleaned and aggregated GeoDataFrame
    return gdf

def rasterize_layer(gdf, layer_name, res_pth, bbox = None, resolution = 5):
    """
    Function to rasterize a vector layer (GeoDataFrame) based on its geometry and
    attribute ('ID'), saving the result as a GeoTIFF file.

    This function takes a GeoDataFrame, a bounding box (bbox), and the desired file
    path for the output rasterized file. It performs the following operations:
    - Transforms the bounding box coordinates into a raster grid.
    - Rasterizes the geometries in the GeoDataFrame by assigning each geometry's
      'ID' value to the corresponding pixel.
    - Saves the rasterized output as a GeoTIFF file.

    :param gdf: GeoDataFrame
        A GeoDataFrame containing vector data (geometries and attributes) that will be rasterized.

    :param layer_name: str
        The name of the layer, used to name the output raster file.

    :param res_pth: str
        The directory path where the output raster file will be saved.

    :param bbox: tuple of float
        A tuple representing the bounding box in the form (minx, miny, maxx, maxy),
        which defines the extent of the rasterized area.

    :param resolution: float
        The resolution (pixel size) of the output raster in the units of the CRS of the input data.

    :return: None
        This function does not return any value, but it saves the rasterized layer as a file
        at the specified `res_pth`.
    """
    startTime = time.time()  # Record start time to measure execution time

    if bbox is None:
        # Define the default bounding box if not provided
        xmn, ymn = 306500, 5973500
        xmx, ymx = 680100, 6257800
        bbox = (xmn, ymn, xmx, ymx)

    # Calculate the transformation matrix for the raster based on the bounding box
    transform = from_bounds(bbox[0], bbox[1], bbox[2], bbox[3],
                            int((bbox[2] - bbox[0]) / resolution),
                            int((bbox[3] - bbox[1]) / resolution))

    # Determine the output shape based on the bounding box size and resolution
    out_shape = (int((bbox[3] - bbox[1]) / resolution),
                 int((bbox[2] - bbox[0]) / resolution))

    # Perform rasterization of the geometries in the GeoDataFrame, assigning 'ID' as the pixel values
    raster = rasterize(
        [(geom, value) for geom, value in zip(gdf.geometry, gdf["ID"])],
        out_shape=out_shape,
        transform=transform,
        fill=0,  # Fill value for areas outside geometries
        dtype="float32"
    )

    # Write the rasterized data to a GeoTIFF file
    with rasterio.open(
            res_pth + layer_name + ".tif",  # Output file path
            "w",  # Write mode
            driver="GTiff",  # GeoTIFF format
            height=out_shape[0],  # Height of the raster grid
            width=out_shape[1],  # Width of the raster grid
            count=1,  # Number of bands (1 for single-band raster)
            dtype="float32",  # Data type of the raster values
            crs=gdf.crs,  # Coordinate Reference System from the GeoDataFrame
            transform=transform  # Transformation matrix to map raster grid to spatial coordinates
    ) as dst:
        dst.write(raster, 1)  # Write the rasterized data to the first band

    # Measure and print the time used for the operation
    time_used(startTime)

    # Return a message indicating the rasterization is complete
    return print(f"{layer_name} rasterized and saved to {res_pth}{layer_name}.tif")

def raster_overlay(first_layer, second_layer, res_pth):
    """
    Function to perform a raster overlay operation between two raster layers.

    This function takes two raster layers (either as NumPy arrays or file paths to GeoTIFF files),
    and merges them by applying a rule: wherever the first raster layer has a pixel value of 0,
    it takes the value from the second raster layer; otherwise, it keeps the value from the first layer.

    :param first_layer: str or np.ndarray
        If a string, it should be the file name of the first raster layer (a GeoTIFF file) to be used in the overlay.
        If a NumPy array, it should contain the raster data for the first layer.

    :param second_layer: str
        The file name of the second raster layer (a GeoTIFF file) to be used in the overlay.

    :param res_pth: str
        The directory path where the raster files are located, which will be combined to form the output.

    :return: np.ndarray
        A NumPy array containing the merged raster data from the overlay operation.
    """
    # Read the first layer data if it's a file path (string), or use the NumPy array directly
    if isinstance(first_layer, np.ndarray):  # Check if it is a NumPy array
        a_data = first_layer
    elif isinstance(first_layer, str):  # If it's a file path, open the raster
        with rasterio.open(res_pth + first_layer + ".tif") as src_a:
            a_data = src_a.read(1)  # Read the first band of A

    # Read the second layer data from the file
    with rasterio.open(res_pth + second_layer + ".tif") as src_b:
        b_data = src_b.read(1)  # Read the first band of B

    # Perform the raster overlay: where the first layer has a value of 0, take the value from the second layer
    merged_data = np.where(a_data == 0, b_data, a_data)

    # Print a message indicating the operation is complete
    print("Data of " + second_layer + " merged into the common raster.")

    # Return the merged raster data
    return merged_data

def get_table_data(db_params):
    """
    Function to retrieve data from a PostgreSQL table using psycopg2.

    This function establishes a connection to a PostgreSQL database using the provided parameters,
    retrieves all rows from a specified table, and prints the rows to the console.

    :param db_params: dict
        A dictionary containing the connection parameters for the PostgreSQL database,
        including the database name, user name, password, host, and port.

    :return: pd.DataFrame
    """
    try:
        # Establish the connection
        conn = psycopg2.connect(**db_params)
        print("Database connection established.")

        # Create a cursor object
        cur = conn.cursor()

        # Define the query
        query = sql.SQL("SELECT * FROM {schema}.{table}").format(
            schema=sql.Identifier('landuse'),
            table=sql.Identifier('landuse_swat_raster_lookup')
        )

        # Execute the query
        cur.execute(query)

        # Fetch all rows
        rows = cur.fetchall()

        # Save into dataframe
        df = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])
        # Close the cursor and connection
        cur.close()
        conn.close()
        return (df)
        print("Database connection closed.")

    except psycopg2.Error as e:
        print(f"An error occurred: {e}")