from __future__ import print_function

import os
import gzip
import time

import utils.path
import db
import db.exceptions

import numpy as np
from sqlalchemy import text
from datetime import datetime


def dump_similarity_column(metric, location, n_recs=None):
    """Create a numpy array dump of similarity vectors for a specific metric.
    Will also create a numpy array dump of lowlevel.ids associated with each
    of the similarity vectors.
    
    Args:
        metric (string): the name of the metric column that should be extracted.
        location (string): directory where archive will be created.
        n_recs (int): number of entries that should be dumped, default is None
        and will extract all entries in similarity.similarity.
    """
    utils.path.create_path(location)
    time_now = datetime.today()

    data_archive_name = "acousticbrainz-similarity-data-{}-{}".format(metric, time_now.strftime("%Y%m%d-%H%M%S"))
    ids_archive_name = "acousticbrainz-similarity-ids-{}-{}".format(metric, time_now.strftime("%Y%m%d-%H%M%S"))

    data_archive_path = os.path.join(location, data_archive_name + ".npy.gz")
    ids_archive_path = os.path.join(location, ids_archive_name + ".npy.gz")

    data_f = gzip.GzipFile(data_archive_path, "w")
    ids_f = gzip.GzipFile(ids_archive_path, "w")

    with db.engine.connect() as connection:
        query = """
            SELECT id
                 , %(metric)s AS metric
              FROM similarity.similarity
        """ % {"metric": metric}
        if n_recs:
            query += "LIMIT :limit"

        query = text(query)
        result = connection.execute(query, {"limit": n_recs})
        if not result.rowcount:
            raise db.exceptions.NoDataFoundException("There is no existing data in the similarity table.")

        recs = []
        ids = []
        for row in result:
            recs.append(row["metric"])
            ids.append(row["id"])

        recs = np.array(recs)
        ids = np.array(ids)
        np.save(file=data_f, arr=recs)
        np.save(file=ids_f, arr=ids)
        data_f.close()
        ids_f.close()


def dump_similarity_by_model(metric, model, location, n_recs=None):
    """Create a numpy array dump of similarity vectors for a specific metric.
    Will also create a numpy array dump of lowlevel.ids associated with each
    of the similarity vectors.
    
    Args:
        metric (string): the name of the metric column that should be extracted.
        model (string): model that will classify each recording.
        location (string): directory where archive will be created.
        n_recs (int): number of entries that should be dumped, default is None
        and will extract all entries in similarity.similarity.
    """
    utils.path.create_path(location)
    time_now = datetime.today()

    data_archive_name = "acousticbrainz-similarity-data-{}-{}-{}".format(metric, model, time_now.strftime("%Y%m%d-%H%M%S"))
    class_archive_name = "acousticbrainz-similarity-class-{}-{}-{}".format(metric, model, time_now.strftime("%Y%m%d-%H%M%S"))

    data_archive_path = os.path.join(location, data_archive_name + ".npy.gz")
    class_archive_path = os.path.join(location, class_archive_name + ".npy.gz")

    data_f = gzip.GzipFile(data_archive_path, "w")
    class_f = gzip.GzipFile(class_archive_path, "w")

    with db.engine.connect() as connection:
        query = """
            WITH hlm AS (
          SELECT highlevel, data->'value' AS value
            FROM highlevel_model AS hlm
            JOIN model
              ON model.id = hlm.model
           WHERE model.model = :model
        """
        if n_recs:
            query += "LIMIT :limit"
        
        query += """)
            SELECT highlevel
                 , %(metric)s AS metric
                 , value
              FROM hlm
         LEFT JOIN similarity.similarity AS s
                ON s.id = hlm.highlevel
        """ % {"metric": metric}

        query = text(query)
        result = connection.execute(query, {"limit": n_recs, "model": model})
        if not result.rowcount:
            raise db.exceptions.NoDataFoundException("There is no existing data in the similarity table.")

        recs = []
        classes = []
        for row in result:
            recs.append(row["metric"])
            classes.append(row["value"])

        recs = np.array(recs)
        classes = np.array(classes)
        np.save(file=data_f, arr=recs)
        np.save(file=class_f, arr=classes)
        data_f.close()
        class_f.close()
