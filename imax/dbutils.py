import logging as lg
import sqlite3
import os
import os
import numpy as np
import random as rn
from .utils import read_config_single

logging = lg.getLogger('utils')

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
    c.execute(
        "create table if not exists CONFIG " "(id int primary key, nimages int , nx int, ny int, updates int default 1)"
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

def merge_db(dbname):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='{}';".format('META'))
    results = c.fetchall()
    if len(results) == 0:
        logging.info("MERGE: Table META does not exist")
    else:
        logging.info("MERGE: Merging tables")
        c.execute("""UPDATE IMAGES
                        SET
                        class = ( select META.class from META  where META.name = IMAGES.name)
                        WHERE
                        EXISTS (
                        SELECT *
                        FROM META
                        WHERE META.name = IMAGES.name)""")
    conn.commit()
    conn.close()



def initialize(images, nimages, NX, NY, NTILES, dbname, configfile):
    logging.info('Initializing {}'.format(dbname))
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
    for i in image_idx:
        vy, vx = np.where(idx == i)
        c.execute("INSERT INTO COORDS VALUES ({},{},{})".format(i, vx[0], vy[0]))
    conn.commit()
    conn.close()
    updates = read_config_single(configfile, 'operation', 'updates')
    if updates:
        update_config(NX, NY, nimages, dbname, 1)
    else:
        update_config(NX, NY, nimages, dbname, 0)
    return idx


def update_config(NX, NY, nimages, userdb, updates=None):
    conn = sqlite3.connect(userdb)
    c = conn.cursor()
    if updates is None:
        c.execute('SELECT updates from CONFIG')
        updates = c.fetchone()[0]
    chunk = [0, nimages, NX, NY, updates]
    c.execute("INSERT or REPLACE INTO CONFIG VALUES (?,?,?,?,?)", chunk)

    conn.commit()
    conn.close()