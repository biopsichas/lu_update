# -*- coding: utf-8 -*-
"""
Script for Geoland data processing. The script reads the data from the specified sources, rasterizes the data, merges
the rasterized layers, and creates statistics for the merged raster. The script uses the functions from the functions.py
file. Land use data is prepared for the LT SWAT model system.

Created on: 2024-11-29
Modified on: 2024-11-29
Author: Svajunas Plunge
Email: svajunas_plunge@sggw.edu.pl

"""
from functions import *

# Switches for the operations (activate as needed)
# 1. Create a rasterized version of the cropped data
rasterize_layers = True
# 2. Merge the rasterized layers into a single raster
merge_rasters = True
# 3. Create statistics for the merged raster
create_statistics = True

# Create a rasterized version of the cropped data
if rasterize_layers:
    startTime_full = startTime = time.time()
    ctr = 1  # Counter for the ID column
    for c, layer in enumerate(data_source.keys()):
        # Data read and coordinates checked
        gdf = gpnd.read_file(data_source[layer][3], bbox=bbox, layer=data_source[layer][2])
        gdf = check_crs(gdf)
        # Only one column "LU" is needed for the rasterization. It is created by cleaning the attributes.
        gdf = clean_attibutes(gdf, data_source[layer][0], data_source[layer][1])
        # The lookup table is created for the legend file
        idx = gdf["LU"].unique()
        lookup_idx = pd.DataFrame({"ID": range(ctr, ctr + len(idx)), "LU": idx})
        # The lookup table is merged with the GeoDataFrame and left with only the ID and geometry columns
        gdf = pd.merge(gdf, lookup_idx, on="LU")
        gdf = gdf[["ID", "geometry"]]
        # The lookup table is saved to a separate file
        df = lookup_idx if ctr == 1 else pd.concat([df, lookup_idx])
        # The GeoDataFrame is rasterized
        rasterize_layer(gdf, layer, cropped_path, bbox, resolution)
        # The counter is updated
        ctr = lookup_idx["ID"].max() + 1

    # Save the ID and LU columns to a separate legend file
    pd.merge(df, gpnd.read_file(gdb_path, layer="globallookup").loc[:, ['globalcode', 'SWATCODE']], left_on='LU',
             right_on='globalcode', how='left').to_csv(cropped_path + 'legend.csv', encoding='utf-8-sig', index=False)
    time_used(startTime)
    print("Data rasterized")
    print("=== STEP 1 is DONE. ===")
    print()

# Merge the rasterized layers into a single raster
if merge_rasters:
    startTime = time.time()
    # Read the cropped raster (the first one is used to get the metadata)
    lyr_base = list(data_source.keys())[0]
    with rasterio.open(cropped_path + lyr_base + ".tif") as src:
        meta = src.meta

    merged = None
    for layer in list(data_source.keys())[1:]:  # Skip the first key by starting from index 1
        # If merged is None (first iteration), use a valid layer file path
        if merged is None:
            merged = raster_overlay(lyr_base, layer, cropped_path)  # The first layer is used as the base
        else:
            merged = raster_overlay(merged, layer, cropped_path)  # Use the previous merged result

    # Update the metadata
    meta.update(dtype=rasterio.float32, count=1)

    # Write the merged raster to a new file
    with rasterio.open(cropped_path + 'merged_output.tif', 'w', **meta) as dst:
        dst.write(merged, 1)

    print("Merged raster saved to " + cropped_path + 'merged_output.tif')
    time_used(startTime)
    print("Data merged")
    print("=== STEP 2 is DONE. ===")
    print()

# Count the number of pixels in each category
if create_statistics:
    startTime = time.time()
    # Open the raster file and read the image
    with rasterio.Env():
        with rasterio.open(cropped_path + 'merged_output.tif') as src:
            image = src.read(1)

            # Count unique values and their frequencies
            unique, counts = np.unique(image, return_counts=True)

            # Create DataFrame with counts and map them with SWATCODE
            pd_values = pd.DataFrame({
                'ID': unique.astype(int),
                'Count': counts,
                'Area_km2': (counts * resolution ** 2) / 1000000  # Convert to km^2 assuming pixel size is 25m x 25m
            })

            # Merge with the id DataFrame
            id = pd.read_csv(cropped_path + 'legend.csv')
            pd_values_transposed = pd.merge(id, pd_values, on = 'ID', how='left')

            # Save detailed sum
            pd_values_transposed.to_csv(cropped_path + 'detailed_sums.csv', encoding='utf-8-sig', index=False)

            # Group by SWATCODE and sum the areas
            pd_values_transposed['SWATCODE'] = pd_values_transposed['SWATCODE'].fillna('Not in legend')
            ppd = pd_values_transposed[['SWATCODE', 'Area_km2']].groupby('SWATCODE', as_index=False).sum()

            # Round the 'Area_km2' column to 2 decimal places
            ppd['Area_km2'] = ppd['Area_km2'].round(2)
            total_area = ppd['Area_km2'].sum()
            ppd['Area_%'] = (ppd['Area_km2'] / total_area) * 100
            ppd['Area_%'] = ppd['Area_%'].round(2)

            # Save summarized sum
            ppd.to_csv(cropped_path + 'sums.csv', encoding='utf-8-sig', index=False)
            # Sort the DataFrame by 'Area_%' in descending order
            ppd_sorted = ppd.sort_values('Area_%', ascending=False)

            # Plotting
            plt.figure(figsize=(10, 6))
            plt.bar(ppd_sorted['SWATCODE'], ppd_sorted['Area_%'], color='skyblue')
            plt.xticks(rotation=90, ha='right')
            plt.xlabel('SWATCODE')
            plt.ylabel('Area (%)')
            plt.title('Area (%) by SWATCODE')
            plt.tight_layout()
            plt.savefig(cropped_path + 'swatcode_area_plot.png', format='png')
            time_used(startTime_full)
            print("Statistics created")
            print("=== STEP 3 is DONE. ===")
            # Show the plot
            plt.show()

# df = get_table_data(db_params)


