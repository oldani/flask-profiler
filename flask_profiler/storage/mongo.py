import time
import pymongo
from base import BaseStorage
import datetime
from bson.objectid import ObjectId


class Mongo(BaseStorage):
    """
    To use this class, you have to provide a config dictionary which contains
    "MONGO_URL", "DATABASE" and "COLLECTION".
    """

    def __init__(self, config=None):
        super(Mongo, self).__init__(),
        self.config = config
        self.mongo_url = self.config.get("MONGO_URL", "mongodb://localhost")
        self.database_name = self.config.get("DATABASE", "flask_profiler")
        self.collection_name = self.config.get("COLLECTION", "measurements")

        def createIndex():
            self.collection.ensure_index(
                [
                    ('startedAt', 1),
                    ('endedAt', 1),
                    ('elapsed', 1),
                    ('name', 1),
                    ('method', 1)]
                )

        self.client = pymongo.MongoClient(self.mongo_url)
        self.db = self.client[self.database_name]
        self.collection = self.db[self.collection_name]
        createIndex()

    def filter(self, kwds={}):
        query = {}
        limit = kwds.get('limit', 100000)
        skip = kwds.get('skip', 0)
        sort_dir = kwds.get('sort', "asc")
        sort_key = kwds.get('sort_by', "_id")

        startedAt = float(kwds.get('startedAt', time.time() - 3600 * 24 * 7))
        endedAt = float(kwds.get('endedAt', time.time()))
        elapsed = float(kwds.get('elapsed', 0))
        name = kwds.get('name', None)
        method = kwds.get('method', None)
        args = kwds.get('args', None)
        kwargs = kwds.get('kwargs', None)

        if sort_dir == "desc":
            sort_dir = pymongo.DESCENDING
        else:
            sort_dir = pymongo.ASCENDING

        if name:
            query['name'] = name
        if method:
            query['method'] = method
        if endedAt:
            query['endedAt'] = {"$lte": endedAt}
        if startedAt:
            query['startedAt'] = {"$gt": startedAt}
        if elapsed:
            query['elapsed'] = {"$gte": elapsed}
        if args:
            query['args'] = args
        if kwargs:
            query['kwargs'] = kwargs

        if limit:
            cursor = self.collection.find(
                query
                ).sort(sort_key, sort_dir).skip(skip)
        else:
            cursor = self.collection.find(
                query
                ).sort(sort_key, sort_dir).skip(skip).limit(limit)
        return (self.clearify(record) for record in cursor)

    def insert(self, recordDictionary):
        result = self.collection.insert(recordDictionary)
        if result:
            return True
        return False

    def truncate(self):
        self.collection.remove()

    def delete(self, measurementId):
        result = self.collection.remove({"_id": ObjectId(measurementId)})
        if result:
            return True
        return False

    def getSummary(self,  kwargs={}):
        match_condition = {}
        endedAt = kwargs.get('endedAt', None)
        startedAt = kwargs.get('startedAt', None)
        elapsed = kwargs.get('elapsed', None)
        name = kwargs.get('name', None)
        method = kwargs.get('method', None)

        if name:
            match_condition['name'] = name
        if method:
            match_condition['method'] = method
        if endedAt:
            match_condition['endedAt'] = {"$lte": endedAt}
        if startedAt:
            match_condition['startedAt'] = {"$gt": startedAt}
        if elapsed:
            match_condition['elapsed'] = {"$gte": elapsed}

        result = self.collection.aggregate([
            {"$match": match_condition},
            {
                "$group": {
                    "_id": {
                        "method": "$method",
                        "name": "$name"
                       },
                    "count": {"$sum": 1},
                    "min": {"$min": "$elapsed"},
                    "max": {"$max": "$elapsed"},
                    "avg": {"$avg": "$elapsed"}
                }
            }
            ])
        return result

    def clearify(self, obj):
        print "----------------------"
        available_types = [int, dict, str, list]
        for k, v in obj.items():
            if any([isinstance(v, av_type) for av_type in available_types]):
                continue
            if k == "_id":
                k = "id"
                obj.pop("_id")
            obj[k] = str(v)
        return obj

    def get(self, measurementId):
        record = self.collection.find_one({'_id': ObjectId(measurementId)})
        return self.clearify(record)
