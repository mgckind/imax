import tornado.ioloop
import tornado.web
import yaml
import os
import numpy as np
import coloredlogs
import sys
import logging
from server_aio import read_config

coloredlogs.install(level=logging.INFO)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        if os.path.exists("local_config.yaml"):
            inyaml = "local_config.yaml"
        else:
            inyaml = "config.yaml"
        logging.info("Reading {}".format(inyaml))
        images, total_images, nimages, dbname, NX, NY, NTILES, MAXZOOM, TILESIZE, config = read_config(
            inyaml, no_read_images=True
        )
        del images
        config["serverPort"] = config["server"]["port"]
        config["serverHost"] = config["server"]["host"]
        config["xdim"] = NX
        config["ydim"] = NY
        config["nimages"] = nimages
        nx = config["xdim"]
        ny = config["ydim"]
        ntiles = int(2 ** np.ceil(np.log2(max(nx, ny))))
        config["tilesX"] = ntiles
        config["tilesY"] = ntiles
        config["maxZoom"] = int(np.log2(ntiles))
        config["minZoom"] = max(config["maxZoom"] - 4, 0)
        tilesize = config["tileSize"]
        config["maxXrange"] = tilesize * nx
        config["maxYrange"] = tilesize * ny
        initial_w = nx * tilesize / int(ntiles / (2 ** config["minZoom"]))
        initial_h = ny * tilesize / int(ntiles / (2 ** config["minZoom"]))
        config["widthDiv"] = min(max(512, initial_w), 3000)
        config["heightDiv"] = min(max(512, initial_h), 800)
        self.render("index.html", **config)


class ConfigHandler(tornado.web.RequestHandler):
    def post(self):
        nx = int(self.get_argument("nx"))
        ny = int(self.get_argument("ny"))
        nim = int(self.get_argument("nim"))
        yaml_file = "local_config.yaml"
        logging.info(" From config, NX = {}, NY={}. {} nimages".format(nx, ny, nim))
        with open("config.yaml", "r") as cfg:
            config = yaml.load(cfg)
        config["xdim"] = nx
        config["ydim"] = ny
        config["nimages"] = nim
        with open(yaml_file, "w") as buf:
            buf.write(yaml.dump(config))
        self.set_status(200)
        self.finish()


def make_app():
    settings = {"template_path": "templates/", "static_path": "static/", "debug": True}
    return tornado.web.Application(
        [(r"/", MainHandler), (r"/config", ConfigHandler)], **settings
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
