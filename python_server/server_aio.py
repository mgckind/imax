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
MAX_WORKERS = None


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
                if os.path.basename(images[ic]) in blacklist:
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


async def update(request):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    gid = request.query["gid"]
    class_input = int(request.query["class"])
    c.execute("UPDATE IMAGES SET class = {} where name = '{}'".format(class_input, gid))
    if class_input >= 0:
        logging.info("UPDATE: {} to class {}".format(gid, class_input))
    else:
        logging.info("CLEAR: {}".format(gid))
    response = web.Response(text="", status=200)
    conn.commit()
    conn.close()
    return response


async def info(request):
    global idx
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    x = int(request.query["x"])
    y = int(request.query["y"])
    ic = idx[y][x]
    c.execute("SELECT name,class FROM IMAGES where id = {}".format(ic))
    try:
        name, classid = c.fetchone()
        logging.info("Selected: x={}, y={}, ic={}".format(x, y, ic))
        st = 200
    except:
        st = 404
        ic = -1
        classid = -1
    if ic >= 0:
        logging.info("Galaxy: {}, Class: {}".format(name, classid))
    else:
        name = ""
    response = web.json_response({'name': name, 'class': classid, 'status': st})
    conn.commit()
    conn.close()
    return response


async def infoall(request):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    c.execute("SELECT id,name,class FROM IMAGES where class >= 0")
    allreturn = c.fetchall()
    logging.info("Getting info for all {} classified tiles".format(len(allreturn)))
    st = 200
    vx = [i[0] % NX for i in allreturn]
    vy = [i[0] // NX for i in allreturn]
    names = [i[1] for i in allreturn]
    classids = [i[2] for i in allreturn]
    response = web.json_response({'names': names, 'classes': classids, 'vx': vx, 'vy': vy, 'status': st})
    conn.commit()
    conn.close()
    return response



async def filter(request):
    global idx
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
    global idx
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
    response = web.Response(text="", status=200)
    return response


async def reset(request):
    global idx, blacklist, images, dbname
    logging.info("RESET: ")
    images, total_images, nimages, dbname, NX, NY, NTILES, MAXZOOM, TILESIZE, config = read_config(
        "config.yaml"
    )
    idx, blacklist = initialize(images, nimages, NX, NY, NTILES)
    # initiate_db(dbname, images)
    response = web.Response(text="", status=200)
    return response


async def redraw(request):
    global idx, blacklist
    blacklist = []
    logging.info("REDRAW: ")
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    c.execute("SELECT name FROM IMAGES where class = 0")
    removeids = c.fetchall()
    for n in removeids:
        blacklist.append(n[0])
    response = web.Response(text="", status=200)
    conn.commit()
    conn.close()

    response = web.Response(text="", status=200)
    return response


async def sort(request):
    global idx
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
    if total_images == 0:
        logging.error("Images not found!. Please check path")
        sys.exit(0)
    dbname = config["dataname"] + ".db"
    logging.info("Total Images in path: {}".format(total_images))
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
    logging.info("No Images displayed: {}".format(nimages))
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
    logging.info('NX x NY = {} x {}'.format(NX,NY))
    return (
        images,
        total_images,
        nimages,
        dbname,
        NX,
        NY,
        NTILES,
        MAXZOOM,
        TILESIZE,
        config,
    )


def create_db(filedb):
    conn = sqlite3.connect(filedb)
    c = conn.cursor()
    c.execute(
        "create table if not exists IMAGES "
        "(id int primary key, display int default 1, name text, class int default -1)"
    )
    conn.commit()
    conn.close()


def initiate_db(filedb, images):
    chunk = [(i, 1, os.path.basename(images[i]), -1) for i in range(len(images))]
    conn = sqlite3.connect(filedb)
    c = conn.cursor()
    c.executemany("INSERT or REPLACE INTO IMAGES VALUES (?,?,?,?)", chunk)
    conn.commit()
    conn.close()


def initialize(images, nimages, NX, NY, NTILES):
    temp = np.zeros(NX * NY, dtype="int") - 1
    image_idx = np.arange(nimages)
    temp[: len(image_idx)] = image_idx
    temp = temp.reshape((NY, NX))
    idx = np.pad(
        temp, ((0, NTILES - NY), (0, NTILES - NX)), "constant", constant_values=-1
    )
    blacklist = []
    return idx, blacklist


if __name__ == "__main__":
    global idx, images, dbname, NX, NY
    logging.basicConfig(level=logging.DEBUG)
    images, total_images, nimages, dbname, NX, NY, NTILES, MAXZOOM, TILESIZE, config = read_config(
        "config.yaml"
    )
    idx, blacklist = initialize(images, nimages, NX, NY, NTILES)
    create_db(dbname)
    initiate_db(dbname, images)
    # Web app
    app = web.Application()
    cors = aiohttp_cors.setup(app)
    cors = aiohttp_cors.setup(
        app,
        defaults={
            # Allow all to read all CORS-enabled resources from clien
            "*": aiohttp_cors.ResourceOptions()
        },
    )
    rnn = cors.add(app.router.add_resource("/random"))
    inf = cors.add(app.router.add_resource("/info"))
    upd = cors.add(app.router.add_resource("/update"))
    get = cors.add(app.router.add_resource("/getall"))
    sor = cors.add(app.router.add_resource("/sort"))
    fil = cors.add(app.router.add_resource("/filter"))
    res = cors.add(app.router.add_resource("/reset"))
    red = cors.add(app.router.add_resource("/redraw"))
    cors.add(rnn.add_route("GET", random))
    cors.add(inf.add_route("GET", info))
    cors.add(get.add_route("GET", infoall))
    cors.add(upd.add_route("GET", update))
    cors.add(sor.add_route("GET", sort))
    cors.add(fil.add_route("GET", filter))
    cors.add(res.add_route("GET", reset))
    cors.add(red.add_route("GET", redraw))
    app.router.add_routes([web.get("/", main)])
    web.run_app(app, port=config["server"]["port"], access_log=None)
