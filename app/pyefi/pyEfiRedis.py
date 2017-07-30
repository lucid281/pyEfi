import redis
from .ttyP import ttyP


class EfiDB():
    def __init__(self, type='sock',
                 hostOrSocket='/var/run/redis/redis.sock',
                 database=0, decode=True
                 ):
        """Setup redis connection here..."""
        try:
            if 'sock' is type:
                self.redisDb = redis.StrictRedis(unix_socket_path=hostOrSocket,
                                                 decode_responses=decode, db=database)
            elif 'ip' is type:
                self.redisDb = redis.StrictRedis(host=hostOrSocket, port=6379,
                                                 decode_responses=decode, db=database)
            else:
                ttyP(7, "redis conf did not work. exiting...")
                exit(1)
        finally:
            # this always prints, helpful debugging
            endc = '\033[0m'
            ttyP(4, "  redis @ " + endc + hostOrSocket)

    def initSubscription(self, channelKey):
        if channelKey.endswith(":"): channelKey = channelKey[:-1]

        self.sub = self.redisDb.pubsub()
        self.sub.subscribe(channelKey)

        endc = '\033[0m'
        ttyP(4, "  subscribed to " + endc + channelKey)
