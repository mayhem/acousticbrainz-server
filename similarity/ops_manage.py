from __future__ import print_function
from flask.cli import FlaskGroup
import click

import webserver
import similarity.paths

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)

@cli.command(name="get-path")
@click.argument("id_1")
@click.argument("id_2")
@click.option("--metric", "-m", default="mfccs", help="Metric that should be used to find path.")
def get_path(id_1, id_2, metric):
    # Find a path (list) of recordings to be played between two recordings.
    similarity.paths.get_vector_midpoint(id_1, id_2, metric)

