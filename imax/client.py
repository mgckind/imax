import tornado.ioloop
import tornado.web
import yaml
import os
import numpy as np
import coloredlogs
import sys
import random as rn
import string
import logging as lg
import sqlite3
import pathlib
from .utils import read_config, read_config_single
from tornado.options import define, options


logging = lg.getLogger('client')
VOWELS = "aeiou"
CONSONANTS = "".join(set(string.ascii_lowercase) - set(VOWELS))

def create_config(inyaml, userdb):
    logging.info("Reading {}".format(inyaml))
    with open(inyaml, "r") as cfg:
        config = yaml.load(cfg, Loader=yaml.FullLoader)
    updates_bool = read_config_single(inyaml, 'operation','updates')
    if updates_bool:
        updates = 1
    else:
        updates = 0
    images, total_images, nimages, NX, NY, NTILES, MAXZOOM, TILESIZE = read_config(
        inyaml, no_read_images=True
    )
    del images
    if os.path.exists(userdb):
        conn = sqlite3.connect(userdb)
        c = conn.cursor()
        c.execute('SELECT nimages, nx, ny, updates from CONFIG')
        nimages, NX, NY, updates = c.fetchone()
        conn.close()
    classes = True
    try:
        if config["classes"] is None:
            classes = False
            config["classes"] = [{"Default": -1}]
    except:
        classes = False
        config["classes"] = [{"Default": -1}]
    config["serverPort"] = config["server"]["port"]
    config["serverHost"] = config["server"]["host"]
    config["rootUrl"] = config["server"]["rootUrl"]
    config["xdim"] = NX
    config["ydim"] = NY
    config["updates"] = updates
    config["buttons"] = {}
    config["buttons"]["help"] = config['operation']['help']
    config["buttons"]["fullscreen"] = config['operation']['fullscreen']
    config["buttons"]["invert"] = config['operation']['invert']
    config["buttons"]["toggle"] = config['operation']['toggle-classes']
    config["buttons"]["random"] = config['operation']['random']
    config["buttons"]["filter"] = config['operation']['filter']
    config["buttons"]["reset"] = config['operation']['reset']
    config["buttons"]["search"] = config['operation']['search']
    config["buttons"]["classes"] = classes
    if not classes:
        config["buttons"]["toggle"] = False
        config["buttons"]["filter"] = False
    config["nimages"] = nimages
    nx = config["xdim"]
    ny = config["ydim"]
    ntiles = int(2 ** np.ceil(np.log2(max(nx, ny))))
    config["tilesX"] = ntiles
    config["tilesY"] = ntiles
    config["maxZoom"] = int(np.log2(ntiles))
    config["minZoom"] = max(config["maxZoom"] - config["display"]["deltaZoom"], 0)
    tilesize = config["display"]["tileSize"]
    config["tileSize"] = tilesize
    config["minYrange"] = config["display"]["minYrange"]
    config["minXrange"] = config["display"]["minXrange"]
    config["maxXrange"] = tilesize * nx
    config["maxYrange"] = tilesize * ny
    initial_w = nx * tilesize / int(ntiles / (2 ** config["minZoom"]))
    initial_h = ny * tilesize / int(ntiles / (2 ** config["minZoom"]))
    min_width = config["display"]["min-width"]
    max_width = config["display"]["max-width"]
    min_height = config["display"]["min-height"]
    max_height = config["display"]["max-height"]
    config["widthDiv"] = min(max(min_width, initial_w), max_width)
    config["heightDiv"] = min(max(min_height, initial_h), max_height)
    return config


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        cc = rn.choices(CONSONANTS, k=8)
        cc[::-2] = rn.choices(VOWELS, k=4)
        username = "".join(cc)
        if not self.get_secure_cookie("username"):
            self.set_secure_cookie("username", username)
            return username
        return self.get_secure_cookie("username").decode('ascii').replace('\"', '')


class MainHandler(BaseHandler):
    def get(self):
        user = self.get_argument('user', None)
        username = user if user is not None else self.current_user
        userdb = os.path.join(options.dbpath, username + '.db')
        inyaml = options.configfile
        config =  create_config(inyaml, userdb)
        config["username"] = username
        self.render("index.html", **config)

def make_app(local):
    tempath = pathlib.Path(__file__).parent.absolute()
    if local:
        path_template = os.path.join('.', 'templates')
        path_static = os.path.join('.', 'static')
    else:
        path_template = os.path.join(tempath, 'templates')
        path_static = os.path.join(tempath, 'static')
    settings = {"template_path": path_template, "static_path": path_static, "debug": True, "cookie_secret": "ABCDEF"}
    return tornado.web.Application(
        [(r"/", MainHandler)], **settings
    )


def run_client(configfile, local):
    if not os.path.exists(configfile):
        logging.error("{} not found. Use config_template.yaml as example".format(configfile))
        logging.error("Exiting")
        sys.exit()
    define("configfile", default=configfile, help="Path to config")
    with open(configfile, "r") as cfg:
        config = yaml.load(cfg, Loader=yaml.FullLoader)
    define("dbpath", default=config['db']['dbpath'], help="Path to sqlite files")
    app = make_app(local)
    port = config["client"]["port"]
    logging.info("======== Running on http://0.0.0.0:{} ========".format(port))
    logging.info("(Press CTRL+C to quit)")
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    run_client()