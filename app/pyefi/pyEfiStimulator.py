import schedule
import time
from .pyEfiTools import PyEfiTools
from .pyEfiRedis import EfiDB
from .ttyP import ttyP

class pyEfiStimulator():
    def __init__(self, channelKey, globalRate):
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

        rpmGen = advSweep(500, 8500, 150)
        def rpm():
            state['rpm'] = int(next(rpmGen))

        rpmdotGen = advSweep(0, 200, 150)
        def rpmdot():
            state['rpmdot'] = int(next(rpmdotGen))

        pulsewidthGen = advSweep(0, 2500, 150)
        def pulsewidth():
            pwm = int(next(pulsewidthGen))
            state['pulsewidth1'] = pwm
            state['pulsewidth2'] = pwm

        batteryGen = basicSweep(110, 150, 10)
        def batteryvoltage():
            state['batteryvoltage'] = int(next(batteryGen))

        tpsGen = basicSweep(0, 1000, 550)
        def tps():
            state['tps'] = int(next(tpsGen))

        coolantGen = advSweep(1500, 2100, 250)
        def coolant():
            state['coolant'] = int(next(coolantGen))

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
        schedule.every(0.0001).seconds.do(rpmdot)
        schedule.every(0.0001).seconds.do(pulsewidth)
        schedule.every(0.0001).seconds.do(batteryvoltage)
        schedule.every(0.0001).seconds.do(tps)
        schedule.every(0.2000).seconds.do(coolant)

        schedule.every(0.0001).seconds.do(commit)

        endc = '\033[0m'
        ttyP(4, f'  pubSubKey @ {endc}stream:{channelKey}')


        try:
            ttyP(0, f'\n    [stim->redis] {globalRate}/s')
            while 1:  # main loop
                schedule.run_pending()
                time.sleep(1 / globalRate)
        except KeyboardInterrupt:  # interrupt loop nicely with ctrl-c
            ttyP(6, '\n  EXITING: KeyboardInterrupt')