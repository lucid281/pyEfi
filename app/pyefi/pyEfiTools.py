import sys
import time
import serial
import json
import struct
import binascii
import configparser
from datetime import datetime
from .ttyP import ttyP


class PyEfiTools:
    def __init__(self):
        self.endc = '\033[0m'  # Clear color and other terminal states

    def canPacketA(self, command=b'A'):
        """create crc32 and packet using pack"""
        packetCrc = binascii.crc32(command)
        self.packetA = struct.pack('>HcL', 1, command, packetCrc)

    # NOT USED kept cuz is only 3 lines and works - but no error checking
    def oldMethod(self):
        self.ser.write(b"A")
        print(f'old method: {self.ser.read(212)}')

    def genByteMappingA(self, iniPath):
        config = configparser.ConfigParser()
        config.sections()
        config.read(iniPath)  # needs to suit your hardware!
        # need to implement a check for a bad config here
        byteLocs = list()  # list of bit positions, eventually sorted
        byteProps = dict()  # dict of bit properties
        self.metricNames = list()
        # copy ConfigParser object into dict, strip out garbage and
        # populate byteLocs, byteProps
        for key in config['OutputChannels']:
            props = config['OutputChannels'][key].split(",")
            props = [x.strip(' ') for x in props]
            props = [x.strip('"') for x in props]

            # if props[0] == "bits":
            # for scalar values set multiplier, bits dont have this
            # create hash from list
            if props[0] == "scalar":
                byteProps[props[2]] = {
                    "name": key,
                    "type": props[0],
                    "size": props[1],
                    "unit": props[3],
                }
                self.metricNames.append(key)
                byteLocs.append(int(props[2]))
                byteProps[props[2]]["multiplier"] = float(props[4])

        # Lets make an unpack string!
        unpkStr = ">"  # big endian!
        # returned string need to be in a precise order
        # hacky -- sorting strings returns 1, 10, 100, 2, etc,
        # so i used a sorted list as an index
        byteLocs = sorted(byteLocs)
        for bitOffset in byteLocs:
            offsetStr = "%s" % bitOffset
            if byteProps[offsetStr]["type"] == "scalar":
                bitSize = byteProps[offsetStr]["size"]
                bitLetter = ""
                # unsigned
                if bitSize == "U08": bitLetter = "B"
                if bitSize == "U16": bitLetter = "H"
                if bitSize == "U32": bitLetter = "L"
                # signed
                if bitSize == "S08": bitLetter = "b"
                if bitSize == "S16": bitLetter = "h"
                if bitSize == "S32": bitLetter = "l"
                unpkStr =+ bitLetter

        # pText = "  ini : %s%s data points in %s bytes" % (
        #         self.endc, len(unpkStr) - 1, struct.calcsize(unpkStr))
        pText = f'  ini : {self.endc}{len(unpkStr) - 1} data points in {struct.calcsize(unpkStr)} bytes'
        ttyP(4, pText)

        # make results available
        self.byteLocs = byteLocs
        self.byteProps = byteProps
        self.byteMapUnpkStr = unpkStr

    def initIni(self, iniFile):
        if iniFile:
            # initialize .ini file for parsing of A command bytes
            self.genByteMappingA(iniFile)
            self.canPacketA()  # pre-can 'A' packet up-front

    def initSerial(self, serialLoc, baud=115200):
        try:
            self.ser = serial.Serial(port=serialLoc,
                                     baudrate=baud,
                                     write_timeout=0.05,
                                     timeout=0.05)
            ttyP(4, "  serial @ " + self.endc + serialLoc)
        except serial.SerialException:
            ttyP(4, "  no serial device available or busy!")
            print("    ", sys.exc_info()[0])
            print("    ", sys.exc_info()[1])
            exit(1)

    def redisSerialCollectLoop(self, redisDb, channelKey):
        """
        Main serial collection loop.

        Takes a Python Redis object already instantiated with a channel subscription
        and a channelKey.
        Hint: For the redisDb object, use EfiDB's wrapper or roll your own Redis connection/sub
        """
        ttyP(4, ("  pubSubKey @ %sstream:%s" % (self.endc, channelKey)))
        try:
            pop = 0
            pop_loop = 0
            t_start = time.time()
            t_pop = time.time()
            print('')
            while True:
                t_packet = time.time()
                dataNow = self.sndRcvA()
                t_loop = time.time()
                if dataNow is None:  # wait to retry
                    time.sleep(1)
                else:
                    dataNow['serialLatency'] = t_loop - t_packet
                    self.pubEvent(redisDb, channelKey, dataNow)
                    pop = pop + 1
                    pop_loop = pop_loop + 1
                    if pop_loop % 60 == 0:
                        t_end = time.time()
                        inLoop = t_end - t_pop
                        rate = pop_loop / inLoop
                        pop_loop = 0
                        t_pop = time.time()
                        if dataNow is not None:  # wait to retry
                            collTxt = "    [ms->redis] %.2f/s\r" % (rate)
                            ttyP(9, collTxt)
        except KeyboardInterrupt:  # interrupt loop nicely with ctrl-c
            t_end = time.time()
            inLoop = t_end - t_start
            rate = pop / inLoop
            ttyP(6, "\n  EXITING: KeyboardInterrupt")

        ttyP(1, "\n  PyEfiTools Runtime Summary:")
        dur = t_end - t_start
        m, s = divmod(dur, 60)
        h, m = divmod(m, 60)
        ttyP(0, "    %s results @ %.2f/s in %.0fh %.0fm %.2fs .\n" %
             (pop, rate, h, m, s))

    def pubEvent(self, redisDb, baseKey, eventPacket):
        """
        Publish an event using an existing connection.

        Example redisConn object
        # redisConn = redis.StrictRedis(
        #     db=0,
        #     unix_socket_path=redisSockPath,
        #     decode_responses=True)
        """
        pubKey = "stream:%s" % baseKey
        indexKey = "collection:%s:index" % baseKey
        statusKey = "collection:%s:status" % baseKey
        dataKey = "collection:%s:data" % baseKey
        timeKey = "collection:%s:time" % baseKey

        if eventPacket:
            # publish to channel
            redisDb.publish(pubKey, json.dumps(eventPacket))
            # pipeline ensures everything happens atomically
            dbPipe = redisDb.pipeline()
            indexNow = redisDb.incr(indexKey)  # incr index counter
            dbPipe.hset(dataKey, indexNow, eventPacket)  # write packet to channel
            dbPipe.zadd(timeKey, eventPacket['time'], indexNow)
            # update collection state
            dbPipe.set(statusKey, 1)
            dbPipe.expire(statusKey, 1)
            dbPipe.execute()

    def sndRcvA(self):
        """send packet, get result, verify, and return"""
        now = datetime.now().strftime("%y%j%H%M%S%f")

        self.ser.write(self.packetA)  # get started by asking for data

        try:
            payloadLengthHeader = self.ser.read(2)
            payloadLength = struct.unpack('>H', payloadLengthHeader)
            rawPayload = self.ser.read(payloadLength[0])  # read payload length

            # now read the crc32 (last 4 bytes)
            rawPayloadCrc = self.ser.read(4)
            payloadCrc = struct.unpack('>L', rawPayloadCrc)

            # gen crc32 of returned data
            rcvdPacketCrc = binascii.crc32(rawPayload)

            # check crc and return
            if payloadCrc[0] == rcvdPacketCrc:
                eventHash = {
                    'time': now,
                    'type': 'pyefi',
                    'length': payloadLength[0],
                    'rawData': rawPayload.hex(),
                    'crc32': rcvdPacketCrc
                }
                # print(self.ser)
                # exit(1)
                return eventHash
            else:
                print("    sndRcvA: BAD CRC32: ", rcvdPacketCrc)
                return None
        except struct.error:
            text = ("    sndRcvA: unpack failed. controller offline? %s\r" %
                    (datetime.now().strftime("%H:%M:%S")))
            ttyP(9, text)
            return None

    def parseEvent(self, eventHash):
        """parse the returned 212 byte array into real values"""
        parsedEvent = eventHash
        parsedEvent["data"] = {}

        try:
            pckt = struct.unpack_from(self.byteMapUnpkStr,
                                      bytes.fromhex(eventHash["rawData"]),
                                      1)  # offset of 1
        except struct.error:
            return None
        # iterate over byte array and match ini file naming
        for idx, metric in enumerate(pckt):
            byteLocation = str(self.byteLocs[idx])
            if self.byteProps[byteLocation]["type"] == 'scalar':
                n = self.byteProps[byteLocation]["name"]
                parsedEvent["data"][n] = metric
        return parsedEvent
