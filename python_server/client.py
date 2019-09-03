import tornado.ioloop
import tornado.web
import yaml
import os
import numpy as np
import coloredlogs
import sys
import random as rn
import string
import logging
import sqlite3
from server_aio import read_config

coloredlogs.install(level=logging.INFO)
VOWELS = "aeiou"
CONSONANTS = "".join(set(string.ascii_lowercase) - set(VOWELS))
DBFILES = 'dbfiles'


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
        username = self.current_user
        userdb = os.path.join(DBFILES, username + '.db')
        inyaml = "config.yaml"
        logging.info("Reading {}".format(inyaml))
        images, total_images, nimages, dbname, NX, NY, NTILES, MAXZOOM, TILESIZE, config = read_config(
            inyaml, no_read_images=True
        )
        del images
        if os.path.exists(userdb):
            conn = sqlite3.connect(userdb)
            c = conn.cursor()
            c.execute('SELECT nimages, nx, ny from CONFIG')
            nimages, NX, NY = c.fetchone()
            conn.close()
        config["serverPort"] = config["server"]["port"]
        config["serverHost"] = config["server"]["host"]
        config["rootUrl"] = config["server"]["rootUrl"]
        config["xdim"] = NX
        config["ydim"] = NY
        config["nimages"] = nimages
        nx = config["xdim"]
        ny = config["ydim"]
        ntiles = int(2 ** np.ceil(np.log2(max(nx, ny))))
        config["tilesX"] = ntiles
        config["tilesY"] = ntiles
        config["maxZoom"] = int(np.log2(ntiles))
        config["minZoom"] = max(config["maxZoom"] - 3, 0)
        tilesize = config["tileSize"]
        config["maxXrange"] = tilesize * nx
        config["maxYrange"] = tilesize * ny
        initial_w = nx * tilesize / int(ntiles / (2 ** config["minZoom"]))
        initial_h = ny * tilesize / int(ntiles / (2 ** config["minZoom"]))
        config["widthDiv"] = min(max(512, initial_w), 3000)
        config["heightDiv"] = min(max(512, initial_h), 800)
        config["username"] = username
        self.render("index.html", **config)


def make_app():
    settings = {"template_path": "templates/", "static_path": "static/", "debug": True, "cookie_secret": "ABCDEF"}
    return tornado.web.Application(
        [(r"/", MainHandler)], **settings
    )


if __name__ == "__main__":
    if not os.path.exists("config.yaml"):
        logging.error("config.yaml not found. Use config_template.yaml as example")
        logging.error("Exiting")
        sys.exit()
    app = make_app()
    with open("config.yaml", "r") as cfg:
        config = yaml.load(cfg)
    port = config["client"]["port"]
    logging.info("======== Running on http://0.0.0.0:{} ========".format(port))
    logging.info("(Press CTRL+C to quit)")
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()
