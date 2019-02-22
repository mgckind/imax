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
import random as rn
import yaml
import coloredlogs
import logging
import asyncio
import requests
import ssl
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
    c.execute("SELECT name,class FROM IMAGES where id = {} order by id".format(ic))
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
    response = web.json_response({"name": name, "class": classid, "status": st})
    conn.commit()
    conn.close()
    return response


async def infoall(request):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    c.execute(
        "SELECT a.id,a.name,a.class,b.vx,b.vy FROM IMAGES a, COORDS b where class >= 0 and display = 1 and a.id = b.id order by a.id"
    )
    allreturn = c.fetchall()
    logging.info("Getting info for all {} classified tiles".format(len(allreturn)))
    st = 200
    # vx = [i[0] % NX for i in allreturn]
    # vy = [i[0] // NX for i in allreturn]
    names = [i[1] for i in allreturn]
    classids = [i[2] for i in allreturn]
    vx = [i[3] for i in allreturn]
    vy = [i[4] for i in allreturn]
    response = web.json_response(
        {"names": names, "classes": classids, "vx": vx, "vy": vy, "status": st}
    )
    conn.commit()
    conn.close()
    return response


async def filter(request):
    global idx, NX, NY, NTILES
    logging.info("FILTER: ")
    checked = request.query["checked"]
    checked = checked.split(",")[:-1]
    logging.info(checked)
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    if len(checked) == 0:
        c.execute("SELECT id FROM IMAGES where display = 1 order by id")
    else:
        c.execute(
            "SELECT id FROM IMAGES where display = 1 and class in ({}) order by id".format(
                ",".join(checked)
            )
        )
    all_ids = c.fetchall()
    all_filtered = [i[0] for i in all_ids]
    if len(all_filtered) > 0:
        default_nx = int(np.ceil(np.sqrt(len(all_filtered))))
        NX = default_nx
        NY = default_nx
        update_config(NX, NY, len(all_filtered))
        NTILES = int(2 ** np.ceil(np.log2(max(NX, NY))))
        logging.info("NX x NY = {} x {}. NTILES = {}".format(NX, NY, NTILES))
    temp = np.zeros(NX * NY, dtype="int") - 1
    image_idx = all_filtered
    temp[: len(image_idx)] = image_idx
    temp = temp.reshape((NY, NX))
    idx = np.pad(
        temp, ((0, NTILES - NY), (0, NTILES - NX)), "constant", constant_values=-1
    )
    c.execute("DELETE FROM COORDS")
    for i in image_idx:
        vy, vx = np.where(idx == i)
        c.execute("INSERT INTO COORDS VALUES ({},{},{})".format(i, vx[0], vy[0]))
    conn.commit()
    conn.close()
    logging.info(" {} images filtered and displayed".format(len(image_idx)))
    response = web.Response(text="", status=200)
    return response


async def random(request):
    global idx, NX, NY, NTILES
    logging.info("RANDOMIZE: ")
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    c.execute("SELECT id FROM IMAGES where display = 1 order by id")
    all_ids = c.fetchall()
    all_displayed = [i[0] for i in all_ids]
    nim = rn.randint(10, nimages)
    default_nx = int(np.ceil(np.sqrt(nim)))
    NX = default_nx
    NY = default_nx
    update_config(NX, NY, nim)
    NTILES = int(2 ** np.ceil(np.log2(max(NX, NY))))
    logging.info("NX x NY = {} x {}. NTILES = {}".format(NX, NY, NTILES))
    temp = np.zeros(NX * NY, dtype="int") - 1
    image_idx = rn.sample(all_displayed, nim)
    temp[: len(image_idx)] = image_idx
    temp = temp.reshape((NY, NX))
    idx = np.pad(
        temp, ((0, NTILES - NY), (0, NTILES - NX)), "constant", constant_values=-1
    )
    c.execute("DELETE FROM COORDS")
    for i in image_idx:
        vy, vx = np.where(idx == i)
        c.execute("INSERT INTO COORDS VALUES ({},{},{})".format(i, vx[0], vy[0]))
    conn.commit()
    conn.close()
    logging.info(" {} images displayed".format(nim))
    response = web.Response(text="", status=200)
    return response


async def reset(request):
    global idx, blacklist, images, dbname
    logging.info("RESET: ")
    images, total_images, nimages, dbname, NX, NY, NTILES, MAXZOOM, TILESIZE, config = read_config(
        "config.yaml", force_copy=True
    )
    idx, blacklist = initialize(images, nimages, NX, NY, NTILES)
    update_config(NX, NY, nimages)
    # initiate_db(dbname, images)
    response = web.Response(text="", status=200)
    return response


async def redraw(request):
    global idx, NX, NY, NTILES, dbname
    logging.info("REDRAW: ")
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    c.execute("SELECT id FROM IMAGES where display = 1 and class != 0 order by id")
    all_ids = c.fetchall()
    all_displayed = [i[0] for i in all_ids]
    images0, total_images, nimages, dbname, NX, NY, NTILES, MAXZOOM, TILESIZE, config = read_config(
        "config.yaml", n_images=len(all_displayed)
    )
    del images0
    update_config(NX, NY, len(all_displayed))
    NTILES = int(2 ** np.ceil(np.log2(max(NX, NY))))
    logging.info("NX x NY = {} x {}. NTILES = {}".format(NX, NY, NTILES))
    temp = np.zeros(NX * NY, dtype="int") - 1
    image_idx = all_displayed
    temp[: len(image_idx)] = image_idx
    temp = temp.reshape((NY, NX))
    idx = np.pad(
        temp, ((0, NTILES - NY), (0, NTILES - NX)), "constant", constant_values=-1
    )
    c.execute("DELETE FROM COORDS")
    for i in image_idx:
        vy, vx = np.where(idx == i)
        c.execute("INSERT INTO COORDS VALUES ({},{},{})".format(i, vx[0], vy[0]))
    conn.commit()
    conn.close()
    logging.info(" {} images displayed".format(len(all_displayed)))
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


def update_config(NX, NY, nimages):
    with open("config.yaml", "r") as cfg:
        config = yaml.load(cfg)
    port = config["client"]["port"]
    host = config["client"]["host"]
    req = requests.post(
        "{}:{}/config".format(host, port), data={"nx": NX, "ny": NY, "nim": nimages}
    )
    yaml_file = dbname.split(".")[0] + ".yaml"
    with open(yaml_file, "r") as buf:
        cfg = yaml.load(buf)
    cfg["xdim"] = NX
    cfg["ydim"] = NY
    cfg["nimages"] = nimages
    with open(yaml_file, "w") as buf:
        buf.write(yaml.dump(cfg))


def read_config(conf, force_copy=False, n_images=None, no_read_images=False):
    with open(conf, "r") as cfg:
        config = yaml.load(cfg)
    if no_read_images:
        images = []
        total_images = 1e9
    else:
        images = glob.glob(os.path.join(config["path"], "*.png"))
        total_images = len(images)
    if total_images == 0:
        logging.error("Images not found!. Please check path")
        sys.exit(0)
    dbname = config["dataname"] + ".db"
    logging.info("Total Images in path: {}".format(total_images))
    nimages = int(config["nimages"])
    if n_images is not None:
        nimages = n_images
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
    config["xdim"] = NX
    config["ydim"] = NY
    config["nimages"] = nimages
    outyaml = config["dataname"] + ".yaml"
    if force_copy:
        with open(outyaml, "w") as out:
            out.write(yaml.dump(config))
    NTILES = int(2 ** np.ceil(np.log2(max(NX, NY))))
    MAXZOOM = np.log2(NTILES)
    TILESIZE = config["tileSize"]
    logging.info(
        "{} max tiles in one side, {} maxzoom, {} maxsize".format(
            NTILES, MAXZOOM, NTILES * TILESIZE
        )
    )
    logging.info("NX x NY = {} x {}".format(NX, NY))
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
    c.execute(
        "create table if not exists COORDS " "(id int primary key, vx int, vy int)"
    )
    conn.commit()
    conn.close()


def initiate_db(filedb, images):
    chunk = [(i, 0, os.path.basename(images[i]), -1) for i in range(len(images))]
    conn = sqlite3.connect(filedb)
    c = conn.cursor()
    c.executemany("INSERT or REPLACE INTO IMAGES VALUES (?,?,?,?)", chunk)
    conn.commit()
    conn.close()


def initialize(images, nimages, NX, NY, NTILES):
    temp = np.zeros(NX * NY, dtype="int") - 1
    image_idx = rn.sample(range(len(images)), nimages)  # np.arange(nimages)
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    c.execute("UPDATE IMAGES SET display = 0")
    c.execute("DELETE FROM COORDS")
    for i in image_idx:
        c.execute("UPDATE IMAGES SET display = 1 where id = {}".format(i))
    c.execute("SELECT id FROM IMAGES where display = 1 order by id")
    all_ids = c.fetchall()
    all_displayed = [i[0] for i in all_ids]
    image_idx = all_displayed
    temp[: len(image_idx)] = image_idx
    temp = temp.reshape((NY, NX))
    idx = np.pad(
        temp, ((0, NTILES - NY), (0, NTILES - NX)), "constant", constant_values=-1
    )
    blacklist = []
    for i in image_idx:
        vy, vx = np.where(idx == i)
        c.execute("INSERT INTO COORDS VALUES ({},{},{})".format(i, vx[0], vy[0]))
    conn.commit()
    conn.close()
    return idx, blacklist


if __name__ == "__main__":
    if not os.path.exists("config.yaml"):
        logging.error("config.yaml not found. Use config_template.yaml as example")
        logging.error("Exiting")
        sys.exit()
    global idx, images, dbname, NX, NY, NTILES
    logging.basicConfig(level=logging.DEBUG)
    images, total_images, nimages, dbname, NX, NY, NTILES, MAXZOOM, TILESIZE, config = read_config(
        "config.yaml", force_copy=True
    )
    with open("config.yaml", "r") as cfg:
        configT = yaml.load(cfg)
    if configT["server"]["ssl"]:
        sslname = configT["server"]["sslName"]
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            "ssl/{}.crt".format(sslname), "ssl/{}.key".format(sslname)
        )
    create_db(dbname)
    initiate_db(dbname, images)
    idx, blacklist = initialize(images, nimages, NX, NY, NTILES)
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
    host = config["server"]["port"]
    port = config["server"]["port"]
    logging.info("======== Running on {}:{} ========".format(host, port))
    logging.info("(Press CTRL+C to quit)")
    if configT["server"]["ssl"]:
        web.run_app(
            app, port=config["server"]["port"], print=None, access_log=None, ssl_context=ssl_context
        )
    else:
        web.run_app(app, port=config["server"]["port"], access_log=None, print=None)
