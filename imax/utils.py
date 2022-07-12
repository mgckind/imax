import logging as lg
import sqlite3
import yaml
import os
import shutil
import numpy as np
import glob
import sys
import pathlib
from shutil import copyfile,copytree
import python_avatars as pa
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import PIL.ImageOps
import cairosvg

logging = lg.getLogger('utils')

def read_config(conf, force_copy=False, n_images=None, no_read_images=False):
    with open(conf, "r") as cfg:
        config = yaml.load(cfg, Loader=yaml.FullLoader)
    if no_read_images:
        images = []
        total_images = 1e9
    else:
        images = sorted(glob.glob(os.path.join(config["display"]["path"], "*.png")))
        total_images = len(images)
    if total_images == 0:
        logging.error("Images not found!. Please check path")
        sys.exit(0)
    logging.info("Total Images in path: {}".format(total_images))
    nimages = int(config["display"]["nimages"])
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
    NX = config["display"]["xdim"]
    NY = config["display"]["ydim"]
    if NX * NY < nimages:
        default_nx = int(np.ceil(np.sqrt(nimages)))
        logging.warning(
            "xdim by ydim ({0}) do not match the nimages({1}).Defaulting to square {2} x {2}".format(
                NX * NY, nimages, default_nx
            )
        )
        NX = default_nx
        NY = default_nx
    config["display"]["xdim"] = NX
    config["display"]["ydim"] = NY
    config["display"]["nimages"] = nimages
    outyaml = conf.replace('.yaml','_copy.yaml')
    if force_copy:
        with open(outyaml, "w") as out:
            out.write(yaml.dump(config))
    NTILES = int(2 ** np.ceil(np.log2(max(NX, NY))))
    MAXZOOM = np.log2(NTILES) 
    DELTAZOOM = config["display"]["deltaZoom"]
    MINZOOM = max(0, MAXZOOM - DELTAZOOM)
    TILESIZE = config["display"]["tileSize"]
    logging.info(
        "{} max tiles in one side, maxzoom = {}, minzoom = {}, maxsize = {} pxs".format(
            NTILES, MAXZOOM, MINZOOM, NTILES * TILESIZE
        )
    )
    logging.info("Input array NX x NY = {} x {}".format(NX, NY))
    logging.info("Actual array NX x NY = {} x {}".format(NX, int(np.ceil(nimages / NX))))
    return (
        images,
        total_images,
        nimages,
        NX,
        NY,
        NTILES,
        MAXZOOM,
        TILESIZE
    )


def read_config_single(conf, arg1, arg2):
    with open(conf, "r") as cfg:
        config = yaml.load(cfg, Loader=yaml.FullLoader)
    return config[arg1][arg2]


def copy_config_template(name):
    tempath = pathlib.Path(__file__).parent.absolute()
    if os.path.exists(name):
        logging.error('File {} exists already'.format(name))
    else:
        logging.info('Creating {} from template'.format(name))
        copyfile(os.path.join(tempath, 'config_template.yaml'), name)


def copy_folders():
    tempath = pathlib.Path(__file__).parent.absolute()
    copytree(os.path.join(tempath, 'static'),'static')
    copytree(os.path.join(tempath, 'templates'),'templates')

def get_cmap(n, name='summer'):
    return plt.cm.get_cmap(name, n)


def create_images(N=100, mapname='summer', folder='images'):
    try:
        shutil.rmtree(folder)
    except:
        pass
    if not os.path.exists(folder):
        os.mkdir(folder)
    else:
        pass
    Nimages = N
    cmap = get_cmap(Nimages, name=mapname)
    chunk = []
    for i in range(Nimages):
        random_avatar = pa.Avatar.random(style=pa.AvatarStyle.TRANSPARENT,background_color=pa.BackgroundColor.WHITE)
        _ = random_avatar.render("test.svg")
        cairosvg.svg2png(url="test.svg", write_to="test.png")
        im = PIL.Image.open("test.png")
        im = im.resize((128,128)).convert("RGBA")
        #cidx = np.random.randint(0,Nmap,1)[0]
        cidx = i
        #print(cidx)
        temp = [int(j*255) for j in cmap(cidx)]
        img = Image.new('RGBA', (128, 128), color = tuple(temp))
        img.paste(im, (0, 0), im)
        d = ImageDraw.Draw(img)
        d.text((5,5), "{}".format(i+1), fill=(0,0,0))
        name = folder+'/{:05}.png'.format(i+1)
        img.save(name)
    os.remove("test.svg")
    os.remove("test.png")

def crop_image(path='', input='', size=128):
    try:
        shutil.rmtree(path)
    except:
        pass
    if not os.path.exists(path):
        os.mkdir(path)
    else:
        pass
    im = Image.open(input)
    imgwidth, imgheight = im.size
    print('Original size {} x {}'.format(imgwidth, imgheight))
    k = 0
    for i in range(0,imgheight,size):
        for j in range(0,imgwidth,size):
            box = (j, i, j+size, i+size)
            a = Image.new('RGB', (size, size), "#dddddd")
            a.paste(im, (-j, -i))
            #a = im.crop(box)
            if np.shape(a) != (size,size,3):
                print(np.shape(a))
            a.save(os.path.join(path,"{:05}.png".format(k)))
            #try:
            ##    #o = a.crop(area)
            #    a.save(os.path.join(path,"PNG","%s" % page,"IMG-%s.png" % k))
            #except:
            #    print('a')
            #    pass
            k +=1
    print('Final X size {}, number of X tiles {}'.format(j+size,(j+size)/size))
    print('Final Y size {}, number of Y tiles {}'.format(i+size,(i+size)/size))
    print('Number of images {}'.format(k))


