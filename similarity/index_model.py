from annoy import AnnoyIndex
from sqlalchemy import text

class AnnoyModel(object):
    def __init__(self, connection, metric_name, n_trees=10, distance_type='angular', load_existing=False):
        """
        Args:
            - metric_name: the name of the metric that vectors in the index will 
              represent, a string.
            - n_trees: the number of trees used in building the index, a positive 
              integer. 
            - distance_type: distance measure, a string. Possibilities are 
              "angular", "euclidean", "manhattan", "hamming", or "dot".
        """
        self.connection = connection
        self.metric_name = metric_name
        self.n_trees = n_trees
        self.distance_type = distance_type
        self.dimension = self.get_vector_dimension()
        self.index = AnnoyIndex(self.dimension, metric=self.distance_type)
        if load_existing:
            self.load(metric_name + '.ann')


    def get_vector_dimension(self):
        """ 
        Get dimension of metric vectors. If there is no metric of this type
        already created then we need to raise an error.
        """
        result = self.connection.execute("""
            SELECT *
            FROM similarity
            LIMIT 1
        """)
        try:
            dimension = len(result.fetchone()[self.metric_name])
            return dimension
        except:
            raise ValueError("No existing metric named \"{}\"".format(metric_name))


    def add_recording_by_mbid(self, mbid, offset):
        # Add a single recording specified by (mbid, offset) to the index.
        # Get id of recording
        # Get metric value for that recording
        # Add it to the index with id as well
        query = text("""
            SELECT *
              FROM similarity
             WHERE id = (
                SELECT id
                  FROM lowlevel
                 WHERE gid = :mbid
                   AND submission_offset = :offset )
        """)
        result = self.connection.execute(query, { "mbid": mbid, "submission_offset": offset})
        row = result.fetchone()
        if row:
            recording_vector = row[self.metric_name]
            id = row['id']
            if not self.index.get_item_vector(id):
                self.index.add_item(id, recording_vector)


    def build(self):
        self.index.build(self.n_trees)


    def save(self):
        name = self.metric_name + '.ann'
        self.index.save(name)


    def load(self, name):
        self.index.load(name)


    def add_recording(self, id, vector):
        if not self.index.get_item_vector(id):
            self.index.add_item(id, vector)