# this is just an example of using matplotlib with pyefi.
# it's not an ideal because matplot uses many cpu cycles.

import redis
from collections import deque

import matplotlib

# ignore PEP E402
matplotlib.use('Qt5Agg')  # needs to be here, before matplotlib.*
import matplotlib.pyplot as plt
import matplotlib.animation as animation

redisDb = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock',
                            decode_responses=True,
                            db=0)


# plot class
class AnalogPlot:
    # constr
    def __init__(self, maxLen):
        self.ax = deque([0.0] * maxLen)
        self.ay = deque([0.0] * maxLen)
        self.maxLen = maxLen

    # add to buffer
    def addToBuf(self, buf, val):
        if len(buf) < self.maxLen:
            buf.append(val)
        else:
            buf.pop()
            buf.appendleft(val)

    # add data
    def add(self, data):
        assert(len(data) == 2)
        self.addToBuf(self.ax, data[0])
        self.addToBuf(self.ay, data[1])

    # update plot
    def update(self, frameNum, a0, a1):
        try:
            top1 = redisDb.zrevrange('pyefi:timeindex', 0, 0, 'withscores')
            # print(top1)
            idnow = top1[0][0]
            rpm = redisDb.hmget("pyefi:events:%s" % idnow, 'rpm')
            rpmdot = redisDb.hmget("pyefi:events:%s" % idnow, 'rpmdot')
            data = []
            data.append(rpm[0])
            data.append(int(rpmdot[0]))

            if(len(data) == 2):
                self.add(data)
                a0.set_data(range(self.maxLen), self.ax)
                a1.set_data(range(self.maxLen), self.ay)
        except KeyboardInterrupt:
            print('exiting')
        # except IndexError:
        #     pass
        return a0, a1


def main():
    print('plotting data...')
    analogPlot = AnalogPlot(200)

    # set up animation
    fig = plt.figure()
    ax = plt.axes(xlim=(0, 200), ylim=(-1000, 8000))
    a0, = ax.plot([], [])
    a1, = ax.plot([], [])
    anim = animation.FuncAnimation(fig, analogPlot.update,
                                   fargs=(a0, a1),
                                   interval=40,
                                   frames=300,
                                   blit=True)

    plt.show()
    # anim.save('animation.mp4', fps=30,
    #           extra_args=['-vcodec', 'libx264'])

    print('exiting.')


# call main
if __name__ == '__main__':
    main()
