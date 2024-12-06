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
import sys

from functions import *

# Switches for the operations (activate as needed)
# 1. Create a rasterized version of the cropped data
rasterize_layers = False
# 2. Merge the rasterized layers into a single raster
merge_rasters = False
# 3. Create statistics for the merged raster
create_statistics = False
# 4. Compare the rasterized data with the previous version
compare_to_previous = False
# 5. Create the final raster for the LT SWAT model and final lookup table for the PostGress database
create_final_raster =True

startTime_full = time.time()
# Create a rasterized version of the data
if rasterize_layers:
    startTime = time.time()
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
    meta.update(dtype=rasterio.int16, count=1)

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
    pd_values = raster_stats(cropped_path + 'merged_output.tif')
    # Merge with the id DataFrame
    id = pd.merge(pd.read_csv(cropped_path + 'legend.csv', usecols=['ID', 'LU']),
                  pd.read_excel('lookup.xlsx'), left_on="LU", right_on="globalcode", how="left")
    pd_values_transposed = pd.merge(id, pd_values, on='ID', how='left')

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

    print("Statistics created")
    time_used(startTime)
    print("=== STEP 3 is DONE. ===")
    print()

# Compare to the previous land use map
if compare_to_previous:
    startTime = time.time()
    # Read the previous land use map
    pd_values = raster_stats(raster_prv)
    id = get_table_data(db_params).rename(columns={'swatcode':'SWATCODE', 'raster_id':'ID'})
    pd_values_transposed = pd.merge(id, pd_values, on='ID', how='left')
    pd_new = pd.read_csv(cropped_path + 'sums.csv')

    df = pd.concat([pd_values_transposed[['SWATCODE', 'Area_km2']].assign(Type='Old'),
                    pd_new[['SWATCODE', 'Area_km2']].assign(Type='New')], axis=0, ignore_index=True)
    df_grouped = df.groupby('Type')['Area_km2'].sum()
    print(df_grouped)
    df_pivot = df.pivot(index='SWATCODE', columns='Type', values='Area_km2')
    df_pivot['new_%'] = round(100 * df_pivot['New'] / df_grouped['New'],2)
    df_pivot['old_%'] = round(100 * df_pivot['Old'] / df_grouped['Old'],2)
    df_pivot['diff_%'] = round(df_pivot['new_%'] - df_pivot['old_%'],2)

    # Sort the DataFrame by 'Area_%' in descending order
    df_pivot_sorted = df_pivot.sort_values('diff_%', ascending=True)
    # Pivot the data so that each SWATCODE has both Old and New areas

    df_pivot.to_csv(cropped_path + 'compare_sums.csv', encoding='utf-8-sig', index=True)
    # Plot configuration

    fig, ax = plt.subplots(figsize=(10, 6))
    df_pivot_sorted['diff_%'].plot(kind='barh', color='skyblue')
    # Add labels and title
    plt.xlabel('Precentage (%)')
    plt.ylabel('SWAT code')
    plt.title('Bar Plot of difference in area (%) by SWAT code (New% - Old%)')
    plt.tight_layout()
    plt.savefig(cropped_path + 'comparison_plot.png', format='png')
    print("Data compared")
    time_used(startTime)
    print("=== STEP 4 is DONE. ===")
    print()

# Create the final raster
if create_final_raster:
    startTime = time.time()
    # Read the lookup tables and create a new
    old_id = pd.read_csv(cropped_path + 'detailed_sums.csv', usecols=['ID', 'SWATCODE'])
    new_id = pd.read_csv(cropped_path + 'compare_sums.csv', usecols=['SWATCODE']).assign(IDn=lambda x: x.index+1)
    lookup_id = pd.merge(old_id, new_id, on='SWATCODE', how='left')
    # Create a lookup dictionary
    lookup_dict = dict(zip(lookup_id['ID'], lookup_id['IDn']))

    # Read raster data
    with rasterio.open(cropped_path + 'merged_output.tif') as src:
        raster_data = src.read(1)  # Read the first band (usually the main raster layer)
        nodata_value = src.nodata
        transform = src.transform
        crs = src.crs

        if nodata_value is None:
            nodata_value = 0
        raster_data[raster_data == 0] = nodata_value
        metadata = src.meta.copy()
        metadata['dtype'] = 'uint8'  # Set data type to uint8
        metadata['nodata'] = nodata_value

        # Modify raster values based on lookup table
        modified_raster = np.copy(raster_data)
        for old_value, new_value in lookup_dict.items():
            modified_raster[raster_data == old_value] = new_value

        modified_raster_uint8 = modified_raster.astype('uint8')
        # Save the modified raster
        with rasterio.open(
                cropped_path + "LUraster.tif",
                'w',
                **metadata
        ) as dest:
            dest.write(modified_raster_uint8, 1)
    # Save the lookup table
    new_id.rename(columns={'SWATCODE': 'swatcode', 'IDn': 'raster_id'}).to_csv(cropped_path + 'landuse_swat_raster_lookup.csv', encoding='utf-8-sig', index=False)
    print("Final raster created and lookup table saved")
    print("Please use 'LUraster.tif' and landuse_swat_raster_lookup.csv' for model update")
    time_used(startTime)
    print("=== STEP 5 is DONE. ===")
    print()

# df = pd.read_csv(cropped_path + 'landuse_swat_raster_lookup.csv')
# df.index = range(1, len(df) + 1)
# connection_string = (
#     f"postgresql://{db_params['user']}:{db_params['password']}"
#     f"@{db_params['host']}:{db_params['port']}/{db_params['dbname']}"
# )
# print(connection_string)
#
# # Database connection using SQLAlchemy
# engine = create_engine(connection_string)
#
# # Rename table if it exists
# table_name_bck = "BACKUP_landuse_swat_raster_lookup"
# table_name = "landuse_swat_raster_lookup"
#
# with engine.connect() as conn:
#     # Rename the table if it exists
#     rename_query = f"""
#     DO $$
#     BEGIN
#         IF EXISTS (SELECT 1 FROM information_schema.tables
#                    WHERE table_schema = 'landuse'
#                    AND table_name = 'landuse_swat_raster_lookup') THEN
#             ALTER TABLE landuse_swat_raster_lookup RENAME TO landuse_swat_raster_lookup_bck;
#         END IF;
#     END $$;
#     """
#     conn.execute(text(rename_query))
#
# # Write the DataFrame to the new table
# # df.to_sql(table_name, engine, if_exists='replace', index=False)
# print(f"Table '{table_name}' created and DataFrame inserted successfully!")


## End of the script
print("=== SCRIPT FINISHED ===")
time_used(startTime_full)