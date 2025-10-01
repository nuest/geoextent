
make the total size in the metadata a flexible unit depending on the size using the humanfriendly library

also use humanfriendly for log outputs where file sizes are mentioned

"no identifiable time extent" should not be a warning but a debug message


---------------

this is not right, there are files smaller than that in the file list

$ geoextent -b -t --max-download-size 100MB 10.25532/OPARA-703
WARNING:geoextent:No files can be downloaded within the size limit
Processing directory: tmprzd2rz5v: 0item [00:00, ?item/s]
WARNING:geoextent:The folder /tmp/tmprzd2rz5v has no identifiable bbox - Coordinate reference system (CRS) may be missing
WARNING:geoextent:The folder /tmp/tmprzd2rz5v has no identifiable time extent
{"format": "remote"}
