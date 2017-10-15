import time
import json
import yaml
import re
import os
from .ttyP import ttyP
from .pyEfiRedis import EfiDB
from .pyEfiTools import PyEfiTools

class RetroDash():
    """
    Redis Data Dashboard -- driven by Redis of course.

    dots split rddString params, commas separate multiple rrdStrings
    when using './pyefi.py dash add'

    rddString Example:
         keyName.label.gfxKey.minVal.maxVal.fireVal.justStr
      rpm.RPM.shiny.0.8000.7000.^5, rpm.RPM.bar.0.8000.7000.<20
    """
    def __init__(self, pyEfiObject, confKey):
        self.endc = '\033[0m'  # Clear color and other terminal states
        self.pyEfi = pyEfiObject
        self.redisDb = pyEfiObject.redisDb
        self.sub = pyEfiObject.sub
        self.confKey = f'dashboard:{confKey}'
        ttyP(4, f'  confKey: {self.endc}{self.confKey}')

    def retroStr(self, confList, inputData):
        # BUG: Not using minValue yet
        keyName, label, gfxKey, minVal, maxVal, fireVal, justStr = confList

        def none():
            colText = ("{:%s}" % (justStr)).format(inputData)
            return colText

        def genericNum():
            value = float(inputData[keyName])
            maxNum = int(maxVal)  # need to test a float here
            # minNum = minValue
            # ANSI color code map - this can be any length
            rainbow = [123, 43, 46, 82, 118, 154, 190,
                       226, 220, 214, 208, 202, 196]
            rainbowLen = len(rainbow)
            # factor up or else int() wont work right with small ints
            maxNum = maxNum * 100
            numNow = value * 100
            # math! use the int results of...
            numStep = int(maxNum / rainbowLen)
            numKey = int(abs(numNow) / numStep)
            # if numKey >= rainbowLen, force numKey to last[#] in array
            if numKey >= rainbowLen: numKey = rainbowLen - 1
            # pas str for cols and set array position(color) + rpm text
            colText = ("{:%s}" % (justStr)).format(inputData[keyName])
            pColText = f'\033[38;5;{rainbow[numKey]}m{colText}\033[0m'
            return pColText

        def bar():
            # color maps, code grows with it automatically -- even steps!
            rainbow = [123, 43, 46, 82, 118, 154, 190,
                       226, 220, 214, 208, 202, 196]
            rainbowLen = len(rainbow)
            colWidth = int(re.sub("[^0-9]", "", justStr))
            value = float(inputData[keyName])
            maxNum = float(maxVal)  # need to test a float here
            # factor up or else int() wont work as desired
            maxNumF = maxNum * 100
            numNowF = value * 100
            colNowF = colWidth * 100
            # math! use the int results of...
            numStep = int(maxNumF / rainbowLen)
            numKey = int(numNowF / numStep)
            if numKey >= rainbowLen: numKey = rainbowLen - 1
            colStep = int(maxNumF / colWidth)
            colKey = int(numNowF / colStep)
            if colKey >= colWidth: colKey = colWidth - 1
            boxes = "\u2501" * colKey
            colText = ("{:%s}" % (justStr)).format(boxes)
            pColText = f'\033[38;5;{rainbow[numKey]}m{colText}\033[0m'
            return pColText

        renderer = {"none": none,
                    "shiny": genericNum,
                    "bar": bar
                    }

        return renderer[gfxKey]()

    def playStream(self, pyEfiObject=None):
        def finalize(deSerialized):
            if 'type' in deSerialized:
                if 'pyefi' in deSerialized['type']:
                    try:
                        final = pyEfiObject.parseEvent(deSerialized)
                    except AttributeError:
                        ttyP(1, "\n Data marked 'pyefi' but no iniFile found to decode data!")
                        ttyP(7, "  Exiting!\n")
                        exit(1)
                elif 'simple' in deSerialized['type']:
                    final = deSerialized
                else:
                    ttyP(1, "\n Data not marked 'pyefi' or 'simple")
                    ttyP(7, "  Exiting!\n")
                    exit(1)
            return final

        try:
            pop = 0
            t_start = time.time()
            for msg in self.sub.listen():
                if msg['type'] == 'message':
                    pop = pop + 1
                    deSerialized = json.loads(msg['data'])
                    self.renderStream(finalize(deSerialized))
        except KeyboardInterrupt:
            t_end = time.time()
            laptime = t_end - t_start
            rate = pop / laptime
            print("\n\nEXITING: KeyboardInterrupt")
            resultsStr = f'{pop} results @ {rate:.2f}/s for {laptime:.2f} seconds.'
            print("\nPyEfiTools Runtime Summary:" + resultsStr)
            exit(0)

    def renderStream(self, data):
        prettyValues = ""
        prettyKeys = ""
        for confEntry in self.redisDb.zrangebyscore(self.confKey, 0, 100):
            try:
                confList = confEntry.split('.')
                # confList [keyName, label, gfxKey, minVal, maxVal, fireVal, justStr]
                keyName, label, gfxKey, minVal, maxVal, fireVal, justStr = confList
                if keyName in data['data']:
                    prettyValues += self.retroStr(confList, data['data'])
                    justifiedText = ("{:%s}" % justStr).format(label)
                    prettyKeys += justifiedText
            except ValueError:
                prettyValues += "!"
                prettyKeys += "!"

        if prettyValues:
            prettyBuffer = f'{prettyValues}\n{prettyKeys}'
            print(prettyBuffer, end='\r', flush=True)


class dashCli:
    def add(self, confKey, position, rddStrings):
        redisDb = EfiDB().redisDb
        rddStrings = rddStrings.strip(' ')
        if ',' in rddStrings:
            ttyP(1, 'adding entries....')
            rrdConfs = rddStrings.split(',')
            for entry in rrdConfs:
                self.checkNadd(redisDb, f'dashboard:{confKey}', position, entry)
        else:
            ttyP(1, 'adding entry....')
            self.checkNadd(redisDb, f'dashboard:{confKey}', position, rddStrings)

    def checkNadd(self, redisDb, confKey, position, entry):
        if redisDb.zrangebyscore(confKey, position, position):
            ttyP(1, f'{confKey} and {position} already exists.')
        else:
            redisDb.zadd(confKey, int(position), entry)
            ttyP(0, f'  {position}  {entry}')

    def rm(self, confKey, rank):
        redisDb = EfiDB().redisDb
        if redisDb.zremrangebyscore(f'dashboard:{confKey}', rank, rank):
            ttyP(1, 'dashboard entry removed')
        else:
            ttyP(7, 'nothing to remove')

    def ls(self):
        redisDb = EfiDB().redisDb
        keys = redisDb.keys('dash*')
        if keys:
            ttyP(4, '\n  found keys:')
            for key in keys:
                ttyP(1, f'    {key}')
                confs = redisDb.zrangebyscore(key, 0, 20, withscores=True)  # top 20 fields
                if confs:
                    for conf, score in confs:
                        niceScore = ("{:%s}" % ("<3")).format(int(score))
                        ttyP(0, f'      {niceScore}  {conf}')
        else:
            ttyP(7, "found nothing!")

    def run(self, channelKey, confKey, iniFile=False):
        """pyEfi Dashboard -- driven by Redis of course."""
        os.system('clear')
        ttyP(1, 'pyefi dashboard')

        channelKey = f'stream:{channelKey}'
        efiDB = EfiDB()
        efiDB.initSubscription(channelKey)
        display = RetroDash(efiDB, confKey)  # setup Retro with our DB and confKey

        if iniFile:
            efi = PyEfiTools()
            efi.initIni(iniFile)
            display.playStream(efi)
        else:
            display.playStream()

    def syncYml(self, ymlFileName='dashboards.yml'):
        redisDb = EfiDB().redisDb
        with open(ymlFileName, 'r') as stream:
            try:
                stateYml = yaml.load(stream)
            except yaml.YAMLError as exc:
                ttyP(7, 'yml load failed.')
                exit(1)
        if 'dashboards' in stateYml:
            for dashboard in stateYml['dashboards']:
                if 'gaugePairs' and 'name' in dashboard:
                    redisDb.delete("dashboard:" + dashboard['name'])
                    ttyP(3, f'\n  {dashboard["name"]}')
                    for position in dashboard['gaugePairs']:
                        rddString = dashboard['gaugePairs'][position]
                        self.checkNadd(redisDb, f'dashboard:{dashboard["name"]}', position, rddString)

    def examples(self):
        ttyP(1, "dashboard entry examples")
        ttyP(7, "\n'QUOTES ARE IMPORTANT'\n")
        ttyP(3, "command examples:")
        ttyP(4, "  ./pyefi.py dash add dashboard:basic '0.rpm.RPM.shiny.0.7500.7000.>5'")
        ttyP(0, "    ^ Add entry '0' with key:'rpm' and label:'RPM' using the 'shiny' style")
        ttyP(0, "      with a min/max of 0/7500 with an alert at 7000. '^5' will print")
        ttyP(0, "      5 characters wide and right justify. ^ = center, < = left\n")
        ttyP(0, "      5 characters wide and right justify. ^ = center, < = left\n")
        ttyP(3, "copy-pastas")
        ttyP(0, "  ./pyefi.py dash add basic '0.rpm.RPM.shiny.0.7500.7000.>4'")
        ttyP(0, "  ./pyefi.py dash add basic '1.rpm.   .bar.0.7500.7000.<20'")
        ttyP(0, "  ./pyefi.py dash add basic '2.rpmdot.DOT.shiny.-4000.4000.3000.>7'")
        ttyP(0, "  ./pyefi.py dash add basic '10.coolant.TEMP.shiny.500.2000.1800.>6'")
        ttyP(0, "  ./pyefi.py dash add basic '20.batteryvoltage.BATT.shiny.0.3000.2500.>6'")