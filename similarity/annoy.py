from annoy import AnnoyIndex
from sqlalchemy import text

class AnnoyModel(object):
    def __init__(self, connection, metric_name, n_trees=10, distance_type='angular'):
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