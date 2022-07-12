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
import logging as lg
import asyncio
import requests
import ssl
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor
from .utils import read_config, read_config_single 
from .dbutils import *

MAX_WORKERS = None
logging = lg.getLogger('server')


def get_tile(x, y, z, inv, idx):
    byteIO = io.BytesIO()
    try:
        if x < 0:
            raise
        if y < 0:
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
                # if os.path.basename(images[ic]) in removelist:
                #     im = Image.new("RGB", (resize, resize), "#dddddd")
                else:
                    im = Image.open(images[ic])
                    im = im.resize((resize, resize))
                    if inv == 1:
                        if np.shape(im)[-1] == 3:
                            im = PIL.ImageOps.invert(im)
                        else:
                            im = PIL.ImageOps.invert(im.convert("RGB"))
                new_im.paste(im, (x_off, y_off))
                y_off += resize
            x_off += resize
        new_im.save(byteIO, "PNG")
        return byteIO.getvalue()
    except Exception as e:
        logging.debug(e)
        return None


async def update(request):
    dbpath = request.app['dbpath']
    userdb = os.path.join(dbpath, request.query["user"] + '.db')
    conn = sqlite3.connect(userdb)
    c = conn.cursor()
    c.execute('SELECT updates from CONFIG')
    updates = c.fetchone()[0]
    if updates == 0:
        logging.info("No UPDATES Allowed")
        response = web.Response(text="", status=200)
        conn.commit()
        conn.close()
        return response
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
    dbpath = request.app['dbpath']
    userdb = os.path.join(dbpath, request.query["user"] + '.db')
    conn = sqlite3.connect(userdb)
    c = conn.cursor()
    x = int(request.query["x"])
    y = int(request.query["y"])
    ic = idx[y][x]
    c.execute("SELECT name,class FROM IMAGES where id = {} order by id".format(ic))
    try:
        name, classid = c.fetchone()
        logging.info("Selected: x={}, y={}, ic={}".format(x, y, ic))
        st = 200
    except Exception as e:
        logging.debug(e)
        st = 404
        ic = -1
        classid = -1
    if ic >= 0:
        logging.info("  Galaxy: {}, Class: {}".format(name, classid))
    else:
        name = ""
    response = web.json_response({"name": name, "class": classid, "status": st})
    conn.commit()
    conn.close()
    return response

async def infoall(request):
    dbpath = request.app['dbpath']
    userdb = os.path.join(dbpath, request.query["user"] + '.db')
    conn = sqlite3.connect(userdb)
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




async def query(request):
    global idx, NX, NY, NTILES
    logging.info("QUERY: ")
    dbpath = request.app['dbpath']
    userdb = os.path.join(dbpath, request.query["user"] + '.db')
    conn = sqlite3.connect(userdb)
    c = conn.cursor()
    qq = request.query["query"]
    #qq = "SELECT name from META where META.name = '00526.png'"
    logging.info("{}".format(qq))
    long_qq = 'select IMAGES.id from IMAGES, ({}) F where IMAGES.name = F.name and IMAGES.display = 1 and IMAGES.class != 0 order by id;'.format(qq)
    try:
        c.execute(long_qq)
        all_ids = c.fetchall()
    except Exception as e:
        logging.error(str(e))
        conn.commit()
        conn.close()
        if qq.strip() == '':
            msg = "Empty query"
        else:
            msg = str(e) 
        response = web.json_response({"msg": msg,  "status": "400"})
        return response
    all_filtered = [i[0] for i in all_ids]
    if len(all_filtered) > 0:
        default_nx = int(np.ceil(np.sqrt(len(all_filtered))))
        NX = default_nx
        NY = default_nx
        update_config(NX, NY, len(all_filtered), userdb)
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
    response = web.json_response({"msg": "ok",  "status": "200"})
    return response



async def filter(request):
    global idx, NX, NY, NTILES
    dbpath = request.app['dbpath'] 
    configfile = request.app['configfile']
    userdb = os.path.join(dbpath, request.query["user"] + '.db')
    logging.info("FILTER: ")
    checked = request.query["checked"]
    checked = checked.split(",")[:-1]
    logging.info(checked)
    conn = sqlite3.connect(userdb)
    c = conn.cursor()
    if len(checked) == 0:
        c.execute("SELECT id FROM IMAGES where display = 1 and class != 0 order by id")
    else:
        c.execute(
            "SELECT id FROM IMAGES where display = 1 and class in ({}) order by id".format(
                ",".join(checked)
            )
        )
    all_ids = c.fetchall()
    all_filtered = [i[0] for i in all_ids]
    if len(all_filtered) > 0:
        if len(checked) == 0:
            images0, total_images, nimages, NX, NY, NTILES, MAXZOOM, TILESIZE = read_config(
                configfile, n_images=len(all_filtered)
            )
            del images0
            update_config(NX, NY, len(all_filtered), userdb)
        else:
            default_nx = int(np.ceil(np.sqrt(len(all_filtered))))
            NX = default_nx
            NY = default_nx
            update_config(NX, NY, len(all_filtered), userdb)
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
    dbpath = request.app['dbpath']
    userdb = os.path.join(dbpath, request.query["user"] + '.db')
    logging.info("RANDOMIZE: ")
    conn = sqlite3.connect(userdb)
    c = conn.cursor()
    c.execute("SELECT id FROM IMAGES where display = 1 and class != 0 order by id")
    all_ids = c.fetchall()
    all_displayed = [i[0] for i in all_ids]
    nim = rn.randint(10, nimages)
    default_nx = int(np.ceil(np.sqrt(nim)))
    NX = default_nx
    NY = default_nx
    update_config(NX, NY, nim, userdb)
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
    global idx, images
    dbpath = request.app['dbpath']
    configfile = request.app['configfile']
    userdb = os.path.join(dbpath, request.query["user"] + '.db')
    logging.info("RESET: ")
    images, total_images, nimages, NX, NY, NTILES, MAXZOOM, TILESIZE = read_config(
        configfile, force_copy=True
    )
    idx = initialize(images, nimages, NX, NY, NTILES, userdb, configfile)
    update_config(NX, NY, nimages, userdb)
    # initiate_db(dbname, images)
    response = web.Response(text="", status=200)
    return response


async def redraw(request):
    global idx, NX, NY, NTILES
    dbpath = request.app['dbpath']
    configfile = request.app['configfile']
    userdb = os.path.join(dbpath, request.query["user"] + '.db')
    logging.info("REDRAW: ")
    conn = sqlite3.connect(userdb)
    c = conn.cursor()
    c.execute("SELECT id FROM IMAGES where display = 1 and class != 0 order by id")
    all_ids = c.fetchall()
    all_displayed = [i[0] for i in all_ids]
    images0, total_images, nimages, NX, NY, NTILES, MAXZOOM, TILESIZE = read_config(
        configfile, n_images=len(all_displayed)
    )
    del images0
    update_config(NX, NY, len(all_displayed), userdb)
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
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    x = int(request.query["x"])
    y = int(request.query["y"])
    z = int(request.query["z"])
    inv = int(request.query["inv"])
    logging.debug("{}, {}, {}, {}".format(x, y, z, inv))
    loop = asyncio.get_running_loop()
    #tile = await request.app.loop.run_in_executor(executor, get_tile, x, y, z, inv, idx)
    tile = await loop.run_in_executor(executor, get_tile, x, y, z, inv, idx)
    if tile is not None:
        response = web.Response(body=tile, status=200, content_type="image/png")
    else:
        response = web.Response(text="", status="404")
    return response


async def init_db(request):
    global idx
    username = request.query["user"]
    dbpath = request.app['dbpath']
    configfile = request.app['configfile']
    userdb = os.path.join(dbpath, username + '.db')
    merge = read_config_single(configfile, 'db', 'merge')
    if not os.path.exists(userdb):
        logging.info("Creating DB for {}".format(username))
        create_db(userdb)
        initiate_db(userdb, images)
        idx = None
    if idx is None:
        logging.info("Creating idx for the first time")
        idx = initialize(images, nimages, NX, NY, NTILES, userdb, configfile)
        if merge:
            merge_db(userdb)
    response = web.Response(text="", status="200")
    return response


def run_server(configfile):
    global idx, images, nimages, NX, NY, NTILES, TILESIZE
    if not os.path.exists(configfile):
        logging.error("{} not found. Use config_template.yaml as example".format(configfile))
        logging.error("Exiting")
        sys.exit()
    with open(configfile, "r") as cfg:
        configT = yaml.load(cfg, Loader=yaml.FullLoader)
    # Web app
    app = web.Application()
    app['dbpath'] = configT['db']['dbpath']
    app['configfile'] = configfile
    dbpath = configT['db']['dbpath'] 
    if not os.path.exists(dbpath):
        os.makedirs(dbpath)
    images, total_images, nimages, NX, NY, NTILES, MAXZOOM, TILESIZE = read_config(
        configfile, force_copy=False
    )
    with open(configfile, "r") as cfg:
        configT = yaml.load(cfg, Loader=yaml.FullLoader)
    if configT["server"]["ssl"]:
        sslname = configT["server"]["sslName"]
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            "ssl/{}.crt".format(sslname), "ssl/{}.key".format(sslname)
        )
    idx = None
    # cors = aiohttp_cors.setup(app)
    cors = aiohttp_cors.setup(
        app,
        defaults={
            # Allow all to read all CORS-enabled resources from client
            "*": aiohttp_cors.ResourceOptions()
        },
    )
    host = configT["server"]["host"]
    port = configT["server"]["port"]
    root = configT["server"]["rootUrl"]
    rnn = cors.add(app.router.add_resource("{rootUrl}random".format(rootUrl=root)))
    inf = cors.add(app.router.add_resource("{rootUrl}info".format(rootUrl=root)))
    upd = cors.add(app.router.add_resource("{rootUrl}update".format(rootUrl=root)))
    get = cors.add(app.router.add_resource("{rootUrl}getall".format(rootUrl=root)))
    sor = cors.add(app.router.add_resource("{rootUrl}sort".format(rootUrl=root)))
    fil = cors.add(app.router.add_resource("{rootUrl}filter".format(rootUrl=root)))
    qry = cors.add(app.router.add_resource("{rootUrl}query".format(rootUrl=root)))
    res = cors.add(app.router.add_resource("{rootUrl}reset".format(rootUrl=root)))
    red = cors.add(app.router.add_resource("{rootUrl}redraw".format(rootUrl=root)))
    ini = cors.add(app.router.add_resource("{rootUrl}initdb".format(rootUrl=root)))
    cors.add(rnn.add_route("GET", random))
    cors.add(inf.add_route("GET", info))
    cors.add(get.add_route("GET", infoall))
    cors.add(upd.add_route("GET", update))
    cors.add(sor.add_route("GET", sort))
    cors.add(fil.add_route("GET", filter))
    cors.add(qry.add_route("GET", query))
    cors.add(res.add_route("GET", reset))
    cors.add(red.add_route("GET", redraw))
    cors.add(ini.add_route("GET", init_db))
    app.router.add_routes([web.get("{rootUrl}".format(rootUrl=root), main)])
    logging.info("======== Running on {}:{}{} ========".format(host, port, root))
    logging.info("(Press CTRL+C to quit)")
    if configT["server"]["ssl"]:
        web.run_app(
            app, port=configT["server"]["port"], print=None, access_log=None, ssl_context=ssl_context
        )
    else:
        web.run_app(app, port=configT["server"]["port"], access_log=None, print=None)


#if __name__ == "__main__":
#    global idx, images, NX, NY, NTILES
#    run_server()
