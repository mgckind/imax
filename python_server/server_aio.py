from aiohttp import web
import aiohttp_cors
import numpy as np
from PIL import Image
import PIL.ImageOps
import io
import os
import sys
import glob
import sqlite3
import yaml
import timeit
import coloredlogs
import logging
import asyncio
import pandas as pd
import random as rn
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor

coloredlogs.install(level=logging.INFO)


def get_tile(x, y, z, inv, idx):
    byteIO = io.BytesIO()
    try:
        if x < 0:
            raise
        new_im = Image.new("RGB", (TILESIZE, TILESIZE), "#dddddd")
        itiles = int(NTILES / (2 ** z))
        resize = int(TILESIZE / itiles)
        x_off = 0
        for ix in range(itiles):
            y_off = 0
            for iy in range(itiles):
                ic = idx[iy + itiles * y][ix + itiles * x]
                if ic == -1:
                    continue
                if images[ic] in blacklist:
                    im = Image.new("RGB", (resize, resize), "#dddddd")
                else:
                    im = Image.open(images[ic])
                    im = im.resize((resize, resize))
                    if inv == 1:
                        im = PIL.ImageOps.invert(im)
                new_im.paste(im, (x_off, y_off))
                y_off += resize
            x_off += resize
        new_im.save(byteIO, "PNG")
        return byteIO.getvalue()
    except Exception as e:
        logging.warning(e)
        return None


MAX_WORKERS = None


async def info(request):
    global idx, df_final
    x = int(request.query["x"])
    y = int(request.query["y"])
    ic = idx[y][x]
    logging.info("Selected: x={}, y={}, ic={}".format(x, y, ic))
    if ic >= 0:
        gid = os.path.basename(images[ic])
        logging.info('Galaxy: {}'.format(gid))
        st = 200
    else:
        gid = ""
        st = 200
    response = web.Response(text=gid, status=st)
    return response


async def filter(request):
    global idx, df_final
    print("FILTER: ")
    image_idx = np.where(df_final.MAG_I.values > 17.5)[0]
    print(df_final.ID.iloc[image_idx])
    print(len(image_idx))
    print(image_idx[0:10])
    temp = np.zeros(NX * NY, dtype="int") - 1
    temp[: len(image_idx)] = image_idx
    temp = temp.reshape((NY, NX))
    idx = np.pad(
        temp, ((0, NTILES - NY), (0, NTILES - NX)), "constant", constant_values=-1
    )
    print(idx[0][0:10])
    response = web.Response(text="", status=200)
    return response


async def random(request):
    global idx, df_final
    logging.info("RANDOMIZE: ")
    temp = np.zeros(NX * NY, dtype="int") - 1
    nim = rn.randint(10, nimages)
    image_idx = np.arange(nim)
    rn.shuffle(image_idx)
    temp[: len(image_idx)] = image_idx
    temp = temp.reshape((NY, NX))
    idx = np.pad(
        temp, ((0, NTILES - NY), (0, NTILES - NX)), "constant", constant_values=-1
    )
    logging.info(" {} images displayed".format(nim))
    images_final = np.array(images)[image_idx].tolist()
    gxs_ids = [os.path.basename(i).replace(".png", "") for i in images_final]
    df_ids = pd.DataFrame(gxs_ids, columns=["ID"])
    df_final = df_all.join(df_ids, how="inner", lsuffix="", rsuffix="right_")
    response = web.Response(text="", status=200)
    return response


async def redraw(request):
    global idx, df_final
    logging.info("REDRAW: ")
    temp = np.zeros(NX * NY, dtype="int") - 1
    image_idx = np.arange(nimages)
    temp[: len(image_idx)] = image_idx
    temp = temp.reshape((NY, NX))
    idx = np.pad(
        temp, ((0, NTILES - NY), (0, NTILES - NX)), "constant", constant_values=-1
    )
    images_final = np.array(images)[image_idx].tolist()
    gxs_ids = [os.path.basename(i).replace(".png", "") for i in images_final]
    df_ids = pd.DataFrame(gxs_ids, columns=["ID"])
    df_final = df_all.join(df_ids, how="inner", lsuffix="", rsuffix="right_")
    response = web.Response(text="", status=200)
    return response


async def sort(request):
    global idx, df_final
    print("SORT: ")
    image_idx = np.argsort(df_final.COLOR1.values)
    temp = np.zeros(NX * NY, dtype="int") - 1
    temp[: len(image_idx)] = image_idx
    temp = temp.reshape((NY, NX))
    idx = np.pad(
        temp, ((0, NTILES - NY), (0, NTILES - NX)), "constant", constant_values=-1
    )
    print(idx[0][0:10])
    response = web.Response(text="", status=200)
    return response


async def main(request):
    global idx, df_final
    executor = ProcessPoolExecutor(max_workers=MAX_WORKERS)
    x = int(request.query["x"])
    y = int(request.query["y"])
    z = int(request.query["z"])
    inv = int(request.query["inv"])
    logging.debug("{}, {}, {}, {}".format(x, y, z, inv))
    tile = await request.app.loop.run_in_executor(executor, get_tile, x, y, z, inv, idx)
    if tile is not None:
        response = web.Response(body=tile, status=200, content_type="image/png")
    else:
        response = web.Response(text="", status="404")
    return response


def read_config(conf):
    with open(conf, "r") as cfg:
        config = yaml.load(cfg)
    images = glob.glob(os.path.join(config["path"], "*.png"))
    total_images = len(images)
    dbname = config["dataname"]+".db"
    logging.info("Total Images: {}".format(total_images))
    nimages = int(config["nimages"])
    if nimages <= 0:
        logging.error("nimages must be positive")
        sys.exit(0)
    if nimages > total_images:
        logging.warning(
            "nimages({}) > total_images({}). Defaulting to total_images".format(
                nimages, total_images
            )
        )
        nimages = total_images
    NX = config["xdim"]
    NY = config["ydim"]
    if NX * NY < nimages:
        default_nx = int(np.ceil(np.sqrt(nimages)))
        logging.warning(
            "xdim by ydim ({0}) do not match the nimages({1}).Defaulting to square {2} x {2}".format(
                NX * NY, nimages, default_nx
            )
        )
        NX = default_nx
        NY = default_nx
    NTILES = int(2 ** np.ceil(np.log2(max(NX, NY))))
    MAXZOOM = np.log2(NTILES)
    TILESIZE = config["tileSize"]
    logging.info(
        "{} max tiles in one side, {} maxzoom, {} maxsize".format(
            NTILES, MAXZOOM, NTILES * TILESIZE
        )
    )
    return images, total_images, nimages, dbname, NX, NY, NTILES, MAXZOOM, TILESIZE


def create_db(filedb):
    conn = sqlite3.connect(filedb)
    c = conn.cursor()
    c.execute("create table if not exists galaxies "
              "(id int primary key, display int default 1, name text, black int default 0)")
    conn.commit()

#def initiate_db(filedb, ):


def initialize(images, nimages, NX, NY, NTILES):
    temp = np.zeros(NX * NY, dtype="int") - 1
    image_idx = np.arange(nimages)
    images_final = np.array(images)[image_idx].tolist()
    gxs_ids = [os.path.basename(i).replace(".png", "") for i in images_final]
    logging.debug("ss")
    df_ids = pd.DataFrame(gxs_ids, columns=["ID"])
    df_final = df_all.join(df_ids, how="inner", lsuffix="", rsuffix="right_")
    temp[: len(image_idx)] = image_idx
    temp = temp.reshape((NY, NX))
    idx = np.pad(
        temp, ((0, NTILES - NY), (0, NTILES - NX)), "constant", constant_values=-1
    )
    blacklist = []
    return idx, blacklist, df_final


if __name__ == "__main__":
    global idx, df_final, images
    logging.basicConfig(level=logging.DEBUG)
    df_all = pd.read_csv("boxall_final.csv")
    images, total_images, nimages, dbname, NX, NY, NTILES, MAXZOOM, TILESIZE = read_config(
        "config.yaml"
    )
    idx, blacklist, df_final = initialize(images, nimages, NX, NY, NTILES)
    create_db(dbname)
    # Web app
    app = web.Application()
    cors = aiohttp_cors.setup(app)
    cors = aiohttp_cors.setup(
        app,
        defaults={
            # Allow all to read all CORS-enabled resources from
            # http://client.example.org.
            "*": aiohttp_cors.ResourceOptions()
        },
    )
    rnn = cors.add(app.router.add_resource("/random"))
    inf = cors.add(app.router.add_resource("/info"))
    sor = cors.add(app.router.add_resource("/sort"))
    fil = cors.add(app.router.add_resource("/filter"))
    red = cors.add(app.router.add_resource("/redraw"))
    cors.add(rnn.add_route("GET", random))
    cors.add(inf.add_route("GET", info))
    cors.add(sor.add_route("GET", sort))
    cors.add(fil.add_route("GET", filter))
    cors.add(red.add_route("GET", redraw))
    app.router.add_routes([web.get("/", main)])
    web.run_app(app, port=8888, access_log=None)
