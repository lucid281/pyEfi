import time
import redis
import pickle
import schedule
# from datetime import datetime
from time import sleep


class PyEfiEyes():
    def __init__(self, pyefiObject, redisSocket='/var/run/redis/redis.sock'):
        self.pyEfi = pyefiObject
        self.pyEfi.redisDb = redis.StrictRedis(
            unix_socket_path=redisSocket,
            decode_responses=True,
            db=0
        )

    def processStream(self):
        try:
            pop = 0
            t_start = time.time()
            while True:
                msg = self.pyEfi.sub.get_message()
                if msg:
                    if msg['type'] == 'message':
                        pyefiData = pickle.loads(msg['data'])
                        finalData = self.pyEfi.parseEvent(pyefiData)
                        print(finalData['serialLatency'])
                        pop = pop + 1
                else:
                    time.sleep(0.002)
        except KeyboardInterrupt:
            t_end = time.time()
            laptime = t_end - t_start
            rate = pop / laptime
            print("\n\nEXITING: KeyboardInterrupt")
            resultsStr = "%s @ %.2f/s for %.2fs" % (pop, rate, laptime)
            print("\nPyEfiTools Runtime Summary:" + resultsStr)
            exit(0)

    def madness(self):
        def fast():
            self.pyEfi.redisDb.incr('pyefi:eye:fast')

        def pollRateTest():
            self.pollRateRedis('pyefi:eye:fast')

        schedule.every(1).seconds.do(pollRateTest)
        schedule.every(0.2).seconds.do(fast)

        while 1:
            schedule.run_pending()

            # This is the scheduler tick rate,
            # nothing will poll faster than this.
            sleep(0.005)

    def pollRateRedis(self, baseKey):
        baseValue = self.pyEfi.redisDb.get(baseKey)
        baseValueLast = self.pyEfi.redisDb.get(baseKey + 'Last')
        self.pyEfi.redisDb.set((baseKey + 'Last'), baseValue)

        if baseValue is None:
            now = 0
        else:
            now = int(baseValue)
        if baseValueLast is None:
            self.pyEfi.redisDb.set((baseKey + 'Last'), baseValue)
            last = int(baseValue)
        else:
            last = int(baseValueLast)
        if now < last:
            last = 0
        rate = now - last
        if rate < 0:
            rate = 0

        print("redis incr: %.2f" % rate)
