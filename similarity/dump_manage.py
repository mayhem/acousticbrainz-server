from __future__ import print_function
from flask.cli import FlaskGroup

import os
import click

import webserver
import db.similarity_dump
import db.similarity_models

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)


@cli.command(name="full")
@click.argument("metric")
@click.option("--location", "-l", default=os.path.join(os.getcwd(), 'export', 'similarity'), show_default=True,
              help="Directory where dump needs to be created.")
@click.option("--n-recs", "-n", default=None, show_default=True,
              help="Number of recordings that should be dumped.")
def similarity_dump(metric, location, n_recs):
    print("Creating similarity dump for metric: {}".format(metric))
    db.similarity_dump.dump_similarity_column(metric, location, n_recs)
    print("Done!")


@cli.command(name="model")
@click.argument("metric")
@click.argument("model")
@click.option("--location", "-l", default=os.path.join(os.getcwd(), 'export', 'similarity'), show_default=True,
              help="Directory where dump needs to be created.")
@click.option("--n-recs", "-n", default=None, show_default=True,
              help="Number of recordings that should be dumped.")
def similarity_dump(metric, model, location, n_recs):
    print("Creating similarity dump for metric: {} with model: {}".format(metric, model))
    db.similarity_dump.dump_similarity_by_model(metric, model, location, n_recs)
    print("Done!")

@cli.command(name="model-plots")
def bulk_get_model_plots():
    db.similarity_models.bulk_get_model_plots(1000)
