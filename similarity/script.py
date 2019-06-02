from __future__ import print_function
from flask.cli import FlaskGroup
import timeit
import click

import webserver
import db

from api import get_all_metrics, get_similar_recordings
from index_model import AnnoyModel

PROCESS_BATCH_SIZE = 10000

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)

mbids=[
    'ebf79ba5-085e-48d2-9eb8-2d992fbf0f6d',
    '8d5f76cf-0fa1-45a1-8464-68053d03b46b',
    'c718f7c1-b63b-4638-bda3-42ca56177dd7',
    '47974dfd-f37d-4f41-b952-18a86af009d2',
    '0cdc9b5b-b16b-4ff1-9f16-5b4ba76f1c17',
    'b7ffa922-7bb8-4703-aa51-3bcc6d9cc364'
]


@cli.command(name='probe-postgres')
def probe_postgres():
    """Get similar recordings using the postgres cube index."""
    print("Probing endpoint for postgres...")
    metrics_dict = get_all_metrics()
    print("====================")
    for mbid in mbids:
        for category, metric_list in metrics_dict.items():
            for metric, _ in metric_list:
                # time = timeit.timeit("get_similar_recordings('{}', '{}')".format(mbid, metric),
                #                      setup='from similarity.api import get_similar_recordings',
                #                      number=1)
                recordings, category, description = get_similar_recordings(mbid, metric)
                print(mbid, metric, category, description)
                print("Similar recordings:")
                print(recordings)
                print("===================")


@cli.command(name='probe-annoy')
def probe_annoy():
    """Get similar recordings using the annoy index."""
    with db.engine.connect() as connection:
        index = AnnoyModel(connection, "mfccs", load_existing=True)
        recordings = index.get_nns(1, 1000)
        print("Similar recordings:")
        print(recordings)
        print("========================")