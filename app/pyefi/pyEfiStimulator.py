import schedule
import time
from .pyEfiTools import PyEfiTools
from .pyEfiRedis import EfiDB
from .ttyP import ttyP

class pyEfiStimulator():
    def __init__(self, channelKey='stim', globalRate=44):
        # globalRate is the scheduler tick rate per second,
        # nothing will update faster than this.
        # Meaning, 'schedule.every(0.001).seconds'
        # wont update 1000/s unless globalRate is set to 1000

        def basicSweep(min, max, rate):
            step = rate / globalRate
            n = min
            rise = True
            while True:
                if rise is True:
                    n += step
                    if n >= max:
                        n = max  # do not yield > max
                        rise = False
                    yield n

                else:
                    n -= step
                    if n <= min:
                        n = min # do not yield < min
                        rise = True
                    yield n

        def advSweep(min, max, rate):
            step = rate / globalRate
            n = min
            rise = True
            while True:
                if rise is True:
                    n += (step + abs(n/100))
                    if n >= max:
                        n = max  # do not yield > max
                        rise = False
                    yield n

                else:
                    n -= (step + abs(n/100))
                    if n <= min:
                        n = min # do not yield < min
                        rise = True
                    yield n


        state = {}

        state['seconds'] = 0
        def seconds():
            state['seconds'] += 1

        rpmGen = advSweep(500, 7000, 50)
        def rpm():
            state['rpm'] = int(next(rpmGen))

        batteryGen = basicSweep(110, 150, 10)
        def batteryvoltage():
            state['batteryvoltage'] = int(next(batteryGen))

        tpsGen = basicSweep(0, 1000, 200)
        def tps():
            state['tps'] = int(next(tpsGen))

        coolantGen = advSweep(1700, 2100, 180)
        def coolant():
            state['coolant'] = int(next(coolantGen))

        mapGen = advSweep(100, 2100, 145)
        def mapG():  # map is used by python
            state['map'] = int(next(mapGen))


        redisDb = EfiDB().redisDb  # setup db connection
        efi = PyEfiTools()  # start up pyEfi
        def commit():
            dataNow = {
                'time': time.time(),
                'type': 'simple',
                'data': state
            }
            efi.pubEvent(redisDb, channelKey, dataNow)


        schedule.every(1).seconds.do(seconds)
        schedule.every(0.0001).seconds.do(rpm)
        schedule.every(0.0001).seconds.do(batteryvoltage)
        schedule.every(0.0001).seconds.do(tps)
        schedule.every(0.2).seconds.do(coolant)
        schedule.every(0.0001).seconds.do(mapG)

        schedule.every(0.0001).seconds.do(commit)


        while 1:  # main loop
            schedule.run_pending()
            time.sleep(1 / globalRate)


# {'seconds': 1341, 'pulsewidth1': 3294, 'pulsewidth2': 3294, 'rpm': 626,
# 'advance': 156, 'squirt': 0, 'engine': 1, 'afrtgt1': 140, 'afrtgt2': 140,
# 'wbo2_en1': 1, 'wbo2_en2': 1, 'barometer': 1000, 'map': 320, 'mat': 699,
# 'coolant': 1799, 'tps': 888, 'batteryvoltage': 149, 'afr1': 169}