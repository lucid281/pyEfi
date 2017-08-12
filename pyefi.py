#!/usr/bin/env python3
import fire
import os
import redis
import time
import random
import string

from app.pyefi.pyEfiStimulator import pyEfiStimulator
from app.pyefi.pyEfiTools import PyEfiTools
from app.pyefi.pyEfiRedis import EfiDB
from app.pyefi.retroDash import dashCli
from app.pyefi.ttyP import ttyP

class Pipeline():
    # These stay in loop
    def run(self):
        """Start stuff."""
        return runCli()

    # Redis Data Dashboard tasks
    def dash(self):
        """Dashboard configuration."""
        return dashCli()

    def test(self):
        """Various tests."""
        return testCli()


class runCli():
    """Processes that run until interrupted by ^C or Redis kill"""
    def dashboard(self, channelKey, confKey, iniFile=False, redisSocket='/var/run/redis/redis.sock'):
        """Hook to dashStage.dashboard()"""
        dashCli.run(self, channelKey, confKey, iniFile, redisSocket)

    def collectMS(self, iniFile, usbLoc, channelKey):
        """Megasquirt Serial -> Redis Collector."""
        os.system('clear')
        ttyP(1, "pyefi collectMS | Megasquirt Serial -> Redis Collector.")

        redisDb = EfiDB().redisDb  # setup db connection
        efi = PyEfiTools()  # start up pyEfi
        efi.initIni(iniFile)  # inform pyEfi of the bytestream structure
        efi.initSerial(usbLoc)  # bring up serial device

        # start serial collection loop with redisDb and specified channelKey
        efi.redisSerialCollectLoop(redisDb, channelKey)

    def stim(self):
        pyEfiStimulator()

class testCli():
    def H(self, count, redisSocket='/var/run/redis/redis.sock'):
        redisDb = redis.StrictRedis(unix_socket_path=redisSocket,
                                    decode_responses=True, db=0)

        sampleData0 = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(512))

        start = time.time()
        for x in range(0, count):
            redisDb.hset('test', x, sampleData0)
        end = time.time()
        dur = end - start
        rate = count / dur
        colTxt = " HSET %s keys in %.4f seconds @ %.0f/s" % (count, dur, rate)
        ttyP(0, colTxt)

        start = time.time()
        for x in range(0, count):
            redisDb.hget('test', x)
        end = time.time()
        dur = end - start
        rate = count / dur
        colTxt = " HGET %s keys in %.4f seconds @ %.0f/s" % (count, dur, rate)
        ttyP(0, colTxt)

        redisDb.delete('test')

if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))  # run everything local to pyefi.py
    fire.Fire(Pipeline)
