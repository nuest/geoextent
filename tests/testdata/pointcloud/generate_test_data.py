#!/usr/bin/env python3
"""Generate small LAS/LAZ test files for geoextent point cloud handler tests.

Run this script to regenerate the test data files:

    .venv/bin/python tests/testdata/pointcloud/generate_test_data.py

All generated files are < 1 KB and contain minimal point data.
"""

import datetime
import os
import numpy as np
import laspy

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def create_las_file(
    filepath,
    points_xyz,
    epsg=None,
    creation_date=None,
    file_version="1.4",
    point_format_id=6,
):
    """Create a minimal LAS file with the given parameters.

    Args:
        filepath: Output file path (.las or .laz)
        points_xyz: Nx3 numpy array of (x, y, z) coordinates
        epsg: EPSG code for CRS (None for no CRS)
        creation_date: datetime.date for LAS header creation date (None for no date)
        file_version: LAS file version string (default "1.4")
        point_format_id: Point format ID (default 6 for LAS 1.4)
    """
    header = laspy.LasHeader(point_format=point_format_id, version=file_version)

    if creation_date is not None:
        header.creation_date = creation_date
    else:
        # Explicitly set to year=0, day=0 to indicate "no creation date"
        # (laspy defaults to today's date otherwise)
        header.creation_date = datetime.date.min  # placeholder, will be zeroed below

    # Set CRS via VLR if EPSG is provided
    if epsg is not None:
        # Use GeoKeyDirectoryTag VLR to store the CRS
        # Key 3072 = ProjectedCSTypeGeoKey (for projected CRS)
        # Key 2048 = GeographicTypeGeoKey (for geographic CRS)
        if epsg == 4326:
            key_id = 2048  # GeographicTypeGeoKey
        else:
            key_id = 3072  # ProjectedCSTypeGeoKey

        vlr = laspy.VLR(
            user_id="LASF_Projection",
            record_id=34735,  # GeoKeyDirectoryTag
            description="GeoTIFF GeoKeyDirectoryTag",
            record_data=_make_geo_key_directory(key_id, epsg),
        )
        header.vlrs.append(vlr)

    # Set offsets and scales based on coordinate range
    if len(points_xyz) > 0:
        header.offsets = np.min(points_xyz, axis=0)
        coord_range = np.max(points_xyz, axis=0) - np.min(points_xyz, axis=0)
        # Use appropriate scale factors
        header.scales = np.where(coord_range > 0, coord_range / 1e6, 1e-6)
    else:
        header.offsets = np.array([0.0, 0.0, 0.0])
        header.scales = np.array([1e-6, 1e-6, 1e-6])

    las = laspy.LasData(header)

    if len(points_xyz) > 0:
        las.x = points_xyz[:, 0]
        las.y = points_xyz[:, 1]
        las.z = points_xyz[:, 2]

    las.write(filepath)

    # Zero out creation date in header if no date was provided
    if creation_date is None:
        import struct

        with open(filepath, "r+b") as fh:
            # LAS 1.4 header: creation_day at offset 90, creation_year at offset 92
            fh.seek(90)
            fh.write(struct.pack("<HH", 0, 0))

    size = os.path.getsize(filepath)
    print(
        f"  Created {os.path.basename(filepath)}: {size} bytes, {len(points_xyz)} points"
    )


def _make_geo_key_directory(key_id, value):
    """Create a minimal GeoTIFF GeoKeyDirectoryTag record.

    The GeoKeyDirectoryTag is a sequence of unsigned shorts:
      [key_directory_version, key_revision, minor_revision, number_of_keys,
       key_id, tiff_tag_location, count, value_offset, ...]

    For simple keys where the value fits in a short, tiff_tag_location=0
    and value_offset is the value itself.
    """
    import struct

    return struct.pack(
        "<8H",
        1,  # key_directory_version
        1,  # key_revision
        0,  # minor_revision
        1,  # number_of_keys
        key_id,  # key_id
        0,  # tiff_tag_location (0 = value is in value_offset)
        1,  # count
        value,  # value_offset (the EPSG code)
    )


def main():
    print("Generating point cloud test data...")

    # 1. WGS84 LAS file (Munster area)
    wgs84_points = np.array(
        [
            [7.5, 51.9, 100.0],
            [7.6, 51.95, 110.0],
            [7.7, 52.0, 120.0],
            [7.55, 51.92, 105.0],
            [7.65, 51.98, 115.0],
        ]
    )
    create_las_file(
        os.path.join(OUTPUT_DIR, "wgs84.las"),
        wgs84_points,
        epsg=4326,
        creation_date=datetime.date(2023, 6, 15),
    )

    # 2. UTM 32N LAS file (projected coordinates)
    utm32n_points = np.array(
        [
            [400000, 5750000, 200.0],
            [400500, 5755000, 250.0],
            [401000, 5760000, 300.0],
            [400200, 5752000, 220.0],
            [400800, 5758000, 280.0],
        ]
    )
    create_las_file(
        os.path.join(OUTPUT_DIR, "utm32n.las"),
        utm32n_points,
        epsg=32632,
        creation_date=datetime.date(2024, 1, 10),
    )

    # 3. No-CRS LAS file (coordinates in WGS84 range but no CRS declared)
    no_crs_points = np.array(
        [
            [7.5, 51.9, 100.0],
            [7.6, 51.95, 110.0],
            [7.7, 52.0, 120.0],
        ]
    )
    create_las_file(
        os.path.join(OUTPUT_DIR, "no_crs.las"),
        no_crs_points,
        epsg=None,
        creation_date=None,
    )

    # 4. Empty LAS file (0 points)
    empty_points = np.empty((0, 3))
    create_las_file(
        os.path.join(OUTPUT_DIR, "empty.las"),
        empty_points,
        epsg=4326,
        creation_date=None,
    )

    # 5. WGS84 LAZ file (compressed, same content as wgs84.las)
    create_las_file(
        os.path.join(OUTPUT_DIR, "wgs84.laz"),
        wgs84_points,
        epsg=4326,
        creation_date=datetime.date(2023, 6, 15),
    )

    print("\nDone! All test files generated in:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
