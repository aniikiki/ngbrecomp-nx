Switch data layout (0.55.0 and newer)

    /switch/ngb-runtime/ngb-startup.nro
    /switch/ngb-runtime/disc/default.xbe
    /switch/ngb-runtime/disc/movie/...
    /switch/ngb-runtime/data/...
    /switch/ngb-runtime/logs/...

Copy the contents of the extracted retail disc to disc/ once. Do not copy an
ISO or the sparse build/switch-runtime/romfs directory. The disc directory is
opened read-only by the game; saves and logs remain in their existing locations.
The NRO embeds the renderer's shader cache, not the extracted game assets.

From the ngbrecomp checkout, with DBI FTP running, use
`python3 packaging/switch/upload-disc.py 10.0.10.150 --port 5000`.
An interrupted first transfer can be run again: completed files are kept.
Replace the NRO after the disc install completes. For later versions built
for this disc layout, transfer only the NRO.
