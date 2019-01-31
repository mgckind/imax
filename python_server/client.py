import tornado.ioloop
import tornado.web
import yaml
import numpy as np
from server_aio import read_config


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        images, total_images, nimages, dbname, NX, NY, NTILES, MAXZOOM, TILESIZE, config = read_config(
            "config.yaml"
        )
        del images
        config["serverPort"] = config["server"]["port"]
        config["xdim"] = NX
        config["ydim"] = NY
        config["nimages"] = nimages
        nx = config["xdim"]
        ny = config["ydim"]
        ntiles = int(2 ** np.ceil(np.log2(max(nx, ny))))
        config["tilesX"] = ntiles
        config["tilesY"] = ntiles
        config["maxZoom"] = int(np.log2(ntiles))
        config["minZoom"] = config["maxZoom"] - 4
        tilesize = config["tileSize"]
        config["maxXrange"] = tilesize * nx
        config["maxYrange"] = tilesize * ny
        initial_w = nx * tilesize / int(ntiles / (2 ** config["minZoom"]))
        initial_h = ny * tilesize / int(ntiles / (2 ** config["minZoom"]))
        config["widthDiv"] = min(max(512, initial_w), 3000)
        config["heightDiv"] = min(max(512, initial_h), 800)
        self.render("index.html", **config)


def make_app():
    settings = {"template_path": "templates/", "static_path": "static/", "debug": True}
    return tornado.web.Application([(r"/", MainHandler)], **settings)


if __name__ == "__main__":
    app = make_app()
    with open("config.yaml", "r") as cfg:
        config = yaml.load(cfg)
    port = config["client"]["port"]
    print("======== Running on http://0.0.0.0:{} ========".format(port))
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()
