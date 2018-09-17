import tornado.ioloop
import tornado.web
import numpy as np
from PIL import Image
import PIL.ImageOps
import io
import glob


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        x = int(self.get_argument("x", '0'))
        y = int(self.get_argument("y", '0'))
        z = int(self.get_argument("z", '0'))
        inv = int(self.get_argument("inv", '0'))
        # print('x={}, y={}, z={}, inv={}'.format(x, y, z, inv))
        self.set_header("Content-type",  "image/png")
        byteIO = io.BytesIO()
        try:
            if x < 0:
                raise
            new_im = Image.new('RGB', (TILESIZE, TILESIZE), '#dddddd')
            itiles = int(NTILES/(2**z))
            resize = int(TILESIZE/itiles)
            x_off = 0
            for ix in range(itiles):
                y_off = 0
                for iy in range(itiles):
                    ic = idx[iy+itiles*y][ix+itiles*x]
                    if ic == -1:
                        continue
                    else:
                        im = Image.open(images[ic])
                        if inv == 1:
                            im = PIL.ImageOps.invert(im)
                        new_im.paste(
                            im.resize((resize, resize)), (x_off, y_off))
                    y_off += resize
                x_off += resize
            new_im.save(byteIO, 'PNG')
            self.write(byteIO.getvalue())
        except Exception as e:
            print(e)
            self.set_status(404)


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ], debug=True)


if __name__ == "__main__":
    images = glob.glob('cutouts/*.png')
    print(len(images))
    NX = 32
    NY = 32
    NTILES = int(2 ** np.ceil(np.log2(max(NX, NY))))
    TILESIZE = 256
    print('{} tiles, {} maxzoom, {} maxsize'.format(
            NTILES, np.sqrt(NTILES), NTILES*TILESIZE))
    temp = np.zeros(NX*NY, dtype='int') - 1
    image_idx = np.arange(1000)
    temp[:len(image_idx)] = image_idx
    temp = temp.reshape((NY, NX))
    idx = np.pad(temp, ((0, NTILES-NY), (0, NTILES-NX)),
                 'constant', constant_values=-1)
    print(idx)
    app = make_app()
    app.listen(8899)
    tornado.ioloop.IOLoop.current().start()
