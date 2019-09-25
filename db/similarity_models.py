from __future__ import absolute_import
import matplotlib
matplotlib.use('Agg')

import plotly.express as px

import os
import time
import gzip
import json

from utils.path import create_path
import db
import similarity.metrics

from sqlalchemy import text
from collections import defaultdict
import numpy as np
from MulticoreTSNE import MulticoreTSNE as TSNE
import pandas as pd
import seaborn as sns

import matplotlib.pyplot as plt
import matplotlib.patheffects as PathEffects

from sklearn.decomposition import PCA
RS = 123


# 18 models
# 70k recordings
# 12 vectors
# One plot for each model, for each of the vectors
def bulk_get_model_plots(sample_size):
    """Get plots of all vectors for a sample of the
    similarity.similarity table, categorized by models"""
    # Get all vecs for each recording from similarity.similarity table
    # And the value of each model for each recording
    # Create numpy array of all vectors
    # Call TSNE on each of the arrays
    # Scatter categorically for each vector array
    location = os.path.join(os.getcwd(), 'plots', 'similarity')
    create_path(location)

    with db.engine.connect() as connection:
        query = text("""
            WITH hlm AS (
          SELECT highlevel
               , jsonb_object_agg(model.model, hlm.data->'value') AS models
            FROM highlevel_model AS hlm
            JOIN model
              ON model.id = hlm.model
        GROUP BY highlevel
           LIMIT :sample_size)
          SELECT *
            FROM hlm
       LEFT JOIN similarity.similarity AS s
              ON s.id = hlm.highlevel
        """)
        result = connection.execute(query, {"sample_size": sample_size})

        metrics = defaultdict(list)
        models = defaultdict(list)
        ids = []
        for row in result:
            ids.append(row["id"])
            for model in row["models"]:
                models[model].append(row["models"][model])
            for metric in similarity.metrics.BASE_METRICS:
                metrics[metric].append(row[metric])

        # print(models)
        # Run TSNE on each array of metric vectors
        # Save data
        create_path(location)
        name = "data_ids"
        data_archive_path = os.path.join(location, name + ".npy.gz")
        data_f = gzip.GzipFile(data_archive_path, "w")
        np.save(file=data_f, arr=ids)
        for metric in metrics:
            data_archive_name = metric
            data_archive_path = os.path.join(location, data_archive_name + ".npy.gz")
            data_f = gzip.GzipFile(data_archive_path, "w")
            tsne = TSNE(n_jobs=5)
            reduced_vectors = tsne.fit_transform(np.array(metrics[metric]))
            np.save(file=data_f, arr=reduced_vectors)
        
        # Only for exporting data for notebook
        for model in models:
            data_archive_name = model
            data_archive_path = os.path.join(location, data_archive_name + "_model.npy.gz")
            data_f = gzip.GzipFile(data_archive_path, "w")
            np.save(file=data_f, arr=models[model])


def scatter(metric, vectors, models):
    # Create scatter coloured for each model
    for model in models:
        # Create colour palette for model values
        # u_models = np.unique(models[model])
        # n_models = len(u_models)
        # palette = iter(sns.color_palette("hls", n_models))
        # colors = {}
        # for cls in u_models:
        #     colors[cls] = next(palette)

        # get_colors = lambda x: colors[str(x)]
        # c = [get_colors(x) for x in list(models[model])]
        # f = plt.figure(figsize=(12, 12))
        # ax = plt.subplot(aspect='equal')
        # sc = ax.scatter(vectors[:, 0], vectors[:, 1], lw=0, s=20, c=c)
        # ax.axis('off')
        # ax.axis('tight')
        # plt.savefig(path)
        # plt.close()
        data = {"x": vectors[:, 0], "y": vectors[:, 1], "model": model}
        df = pd.DataFrame(data=data)
        fig = px.scatter(df, hover_data=['model'], color='model')
        fig.show()
        path = os.path.join(os.getcwd(), 'plots', 'similarity', metric + '__' + model + '.png')
        fig.write_image(path)
