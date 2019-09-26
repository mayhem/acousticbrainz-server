import db
import db.similarity
from similarity.index_model import AnnoyModel

import numpy as np
# Query for vectors for two recordings

##### Option 1 #####
# Pick a song to start.
# Pick a song to finish.
# ** For now, pick a metric to go by **
# Query Annoy for distance between the two songs
# Query Annoy for similar recordings to the first song, in terms of that metric
# Search for similar recording, then query for distance between this recording and the final recording
# Pick similar recording that reduces distance
# Repeat with this as the starting song


##### Option 2 #####
# Pick a recording to start
# Pick a recording to finish
# Pick a metric
# Query for vectors for the two recordings
# Compute position vector of midpoint between two recordings
# Add this vector to Annoy index and query for the most similar recordings
# Pick the most similar recording (nearest vector), or use something like recommendations to choose the similar recording
# Or find most similar recordings for all metrics, pick a recording that overlaps as "similar" according to multiple metrics
# Recursively repeat to identify more midpoint recordings

def get_path(id_1, id_2, metric):
    path = [id_1]
    index = AnnoyModel(metric, load_existing=True)
    rec_1 = db.similarity.get_similarity_row_id(id_1)
    rec_2 = db.similarity.get_similarity_row_id(id_2)
    vec_1 = rec_1[metric]
    vec_2 = rec_2[metric]
    get_path_recursively(vec_1, path, index)


def get_path_recursively(vec_1, path, index):
    


def get_vector_midpoint(vec_1, vec_2):
    return np.divide(np.add(vec_1, vec_2), 2)
