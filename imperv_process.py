from functions import *
from rasterio.features import shapes
from shapely.geometry import shape

geo_path = "G:\\LIFE_AAA\\swat_lt\\Data\\LandUse\\Geoland\\imperv.tif"
with rasterio.open(geo_path) as src:
    data = src.read(1)
    data = np.where((data > 0) & (data <= 18), 1,
                              np.where((data > 18) & (data <= 26), 2,
                                       np.where((data > 26) & (data <= 44), 3,
                                                np.where((data > 44) & (data <= 82), 4,
                                                         np.where((data > 82) & (data <= 100), 5, 0)))))
    data = data.astype(np.uint8)
    mask = data != 0  # Mask out zero values
    shapes_gen = shapes(data, mask=mask, transform=src.transform)
    # Create a list of geometries and values
    geoms = []
    for geom, value in shapes_gen:
        if value != 0:  # Skip the value 0
            geoms.append({
                'geometry': shape(geom),
                'value': value
            })

    # Create a GeoDataFrame from the list of geometries
    gdf = gpnd.GeoDataFrame(geoms, crs=src.crs)
    gdf['Cat'] = gdf.apply(
        lambda row: 'URLD' if row['value'] == 1
        else 'URML' if row['value'] == 2
        else 'URMD' if row['value'] == 3
        else 'URHD' if row['value'] == 4
        else 'UIDU' if row['value'] == 5
        else None,
        axis=1
    )
    gdf = check_crs(gdf)
    # Save the result to a shapefile
    gdf = gdf[["Cat", "geometry"]]
    gdf.to_file("G:\\LIFE_AAA\\swat_lt\\Data\\LandUse\\Landuse_update\\2024\\inputs\\imperv2024.gpkg", layer='imperv', driver="GPKG")
    print(gdf.head())
