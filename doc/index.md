# Teledetection

<p align="center">
<img src="logo.png" width="320px">
<br>
<a href="https://forgemia.inra.fr/cdos-pub/teledetection/-/releases">
<img src="https://forgemia.inra.fr/cdos-pub/teledetection/-/badges/release.svg">
</a>
<a href="https://forgemia.inra.fr/cdos-pub/teledetection/-/commits/main">
<img src="https://forgemia.inra.fr/cdos-pub/teledetection/badges/main/pipeline.svg">
</a>
<a href="LICENSE">
<img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg">
</a>
</p>

**`teledetection`** enables to use the STAC based geospatial data infrastructure of [*la Maison de la Teledetection*](https://www.teledetection.fr/index.php/en/), also known as *MTD*.
In particular, it enables:

- Accessing catalogs based on the MTD STAC infrastructure *(URLs provided by our STAC URLs are not signed, hence not accessible)*,
- Publishing local STAC objects and transfer files on the MTD STAC infrastructure. 

## Installation and requirements

### For data users

```commandline
pip install teledetection
```

The `teledetection` software development kit (SDK) works like 
[Microsoft Planetary Computer SDK](https://github.com/microsoft/planetary-computer-sdk-for-python)
on which it has heavily been inspired.

### For data producers

```commandline
pip install teledetection[upload]
```

Data producers are invited to take a look [here](sample.md) to see how to 
generate a pystac catalog, or check in detail the 
[pystac documentation](https://pystac.readthedocs.io/en/stable/tutorials.html),
then read in the [upload section](upload.md).

## Contribute

You can open issues or merge requests at 
[INRAE's gitlab](https://forgemia.inra.fr/cdos-pub/teledetection).
