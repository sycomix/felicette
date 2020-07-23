import rasterio as rio
import numpy as np
from rio_color import operations, utils
from PIL import Image
import PIL
from rich import print as rprint

from felicette.utils.color import color
from felicette.utils.gdal_pansharpen import gdal_pansharpen
from felicette.utils.file_manager import file_paths_wrt_id
from felicette.utils.image_processing_utils import process_sat_image

# increase PIL image processing pixels count limit
PIL.Image.MAX_IMAGE_PIXELS = 933120000


def process_landsat_ndvi(id, bands=[4,5]):
    band4 = rasterio.open('LC81430542020100-b4.tiff') #red
    band5 = rasterio.open('LC81430542020100-b5.tiff') #nir

    #generate nir and red objects as arrays in float64 format
    red = band4.read(1).astype('float64')
    nir = band5.read(1).astype('float64')

    ndvi = (nir - red) / (nir+red)
    #export ndvi image
    ndvi_image = rasterio.open('ndvi.tiff','w',driver='Gtiff',
                              width=band4.width,
                              height = band4.height,
                              count=1, crs=band4.crs,
                              transform=band4.transform,
                              dtype='float64')
    ndvi_image.write(ndvi,1)
    ndvi_image.close()


def process_landsat_data(id, bands=[2, 3, 4]):

    # get paths of files related to this id
    paths = file_paths_wrt_id(id)

    # stack R,G,B bands

    # open files from the paths, and save it as stack
    b4 = rio.open(paths["b4"])
    b3 = rio.open(paths["b3"])
    b2 = rio.open(paths["b2"])

    # read as numpy ndarrays
    r = b4.read(1)
    g = b3.read(1)
    b = b2.read(1)

    with rio.open(
        paths["stack"],
        "w",
        driver="Gtiff",
        width=b4.width,
        height=b4.height,
        count=3,
        crs=b4.crs,
        transform=b4.transform,
        dtype=b4.dtypes[0],
        photometric="RGB",
    ) as rgb:
        rgb.write(r, 1)
        rgb.write(g, 2)
        rgb.write(b, 3)
        rgb.close()

    source_path_for_rio_color = paths["stack"]

    # check if band 8, i.e panchromatic band has to be processed
    if 8 in bands:
        # pansharpen the image
        rprint(
            "Pansharpening image, get ready for some serious resolution enhancement! ✨"
        )
        gdal_pansharpen(["", paths["b8"], paths["stack"], paths["pan_sharpened"]])
        # set color operation's path to the pansharpened-image's path
        source_path_for_rio_color = paths["pan_sharpened"]

    rprint("Let's make our 🌍 imagery a bit more colorful for a human eye!")
    # apply rio-color correction
    ops_string = "sigmoidal rgb 20 0.2"
    # refer to felicette.utils.color.py to see the parameters of this function
    # Bug: number of jobs if greater than 1, fails the job
    color(
        1,
        "uint16",
        source_path_for_rio_color,
        paths["output_path"],
        ops_string.split(","),
        {"photometric": "RGB"},
    )

    # resize and save as jpeg image
    print("Generated 🌍 images!🎉")
    rprint("[yellow]Please wait while I resize and crop the image :) [/yellow]")
    process_sat_image(paths["output_path"], paths["output_path_jpeg"])
    rprint("[blue]GeoTIFF saved at:[/blue]")
    print(paths["output_path"])
    rprint("[blue]JPEG image saved at:[/blue]")
    print(paths["output_path_jpeg"])
