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

class MainCli():
    def run(self):
        """Long running processes"""
        return runCli()

    # Redis Data Dashboard tasks
    def dash(self):
        """Dashboard configuration."""
        return dashCli()  # from retroDash.py

    def test(self):
        """Various tests."""
        return testCli()


class runCli():
    """Processes that run until interrupted by ^C or Redis kill"""
    def dashboard(self, channelKey, confKey, iniFile=False):
        """Hook to dashStage.dashboard()"""
        dashCli.run(self, channelKey, confKey, iniFile)

    def collectMS(self, iniFile, serialLoc, channelKey):
        """Megasquirt Serial -> Redis Collector."""
        os.system('clear')
        ttyP(1, 'pyefi collectMS')

        redisDb = EfiDB().redisDb  # setup db connection
        efi = PyEfiTools()  # start up pyEfi
        efi.initIni(iniFile)  # inform pyEfi of the bytestream structure
        efi.initSerial(serialLoc)  # bring up serial device

        # start serial collection loop with redisDb and specified channelKey
        efi.redisSerialCollectLoop(redisDb, channelKey)

    def stim(self, channelKey, rate=44):
        """Lightweight collectMS simulator"""
        ttyP(1, 'pyefi stimulator')
        pyEfiStimulator(channelKey, rate)

class testCli():
    def H(self, count, length=512):
        ttyP(2, f'pyEfi redis benchmark:')
        ttyP(3, f'  {count} entries with {length} characters')
        redisDb = EfiDB().redisDb
        sampleData = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))

        ttyP(4, '\nHSET')
        start = time.time()
        for x in range(0, count):
            redisDb.hset('test', x, sampleData)
        end = time.time()
        dur = end - start
        rate = count / dur
        colTxt = f'  {dur:.5f} seconds @ {rate:.0f}/s'
        ttyP(0, colTxt)

        ttyP(4, 'HGET')
        start = time.time()
        for x in range(0, count):
            redisDb.hget('test', x)
        end = time.time()
        dur = end - start
        rate = count / dur
        colTxt = f'  {dur:.5f} seconds @ {rate:.0f}/s'
        ttyP(0, colTxt)

        redisDb.delete('test')

if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))  # run everything local to pyefi.py
    fire.Fire(MainCli)
