# PyEfi

```
pyEfi
├── app
│   ├── pyefi
│   │   ├── pyEfiTools.py  # megasquirt tools
│   │   ├── retroDash.py   # data stream terminal printer
│   │   ├── pyEfiRedis.py  # redis tools
│   │   ├── pyEfiEyes.py   # data processing
│   │   └── ttyP.py        # quick/simple terminal printer
├── README.md
├── microsquirt.ini        # serial data structure definition
├── pyefi.py               # cli wrapper
├── .tmuxp.yaml            # conf to create a predefined environment
├── dashboards.yml         # dashboard configs
└── console                # execs  .tmuxp.yaml
```

> Tested on Debian 9, Ubuntu 16/17, Manjaro 17 -- probably ok on OSx, probably not Windows.

This is an experimental tool. No warranty expressed or implied. I am not responsible for any damages to you, people around you, or your vehicle.

## Intro
pyEfi is a set of tools in cli form used to gather data from Megasquirt ECU's via the serial interface, store and publish that data via a Redis unix socket, then display and process that data in different ways. pyEfi can currently collect, process and display data 40+ times a second for an 'A' command, all while keeping cpu usage under 10% on a Core2 Q6600 @ 2.40GHz.

Every action is handled via the pyEfi cli. For collection operations, state is determined at runtime. After each collection, data is saved then published to a Redis channel.

For display operations, configuration is stored in Redis. Display configuration is read in every time a published message is read. Effective updating

Separate processes act on each published message, freeing up the main collection loop(s). Each process adds to the database depending on need and should allow for some more freedom in the future.

The 'Redis Data Display' as I call it, reads in metric data AND its display parameters from Redis. Once subscribed to a Redis pub/sub channel, each message updates the display and configuration.

## Install the things
The `apt` commands are for Debian based distros, adjust for other GNU + Linuxes.
- need these for python: `apt install curl zlibc tmux`
- install pyenv: [pyenv @ GitHub](https://github.com/pyenv/pyenv#installation)
- install python 3.6.2: `pyenv install 3.6.2`
- install python packages: `pip install -r requirements.txt`
- install Redis (debian): `apt install redis-server`

## Configure Redis
```
# redis conf: /etc/redis/redis.conf
# unix socket
unixsocket /var/run/redis/redis.sock
unixsocketperm 660
```
restart redis: `service redis restart`


## misc
#### Serial Permissions and Latency
Older versions of the Linux kernel set `latency_timer` to `1`. The 4.x kernels I've tried set `latency_timer` to `16` by default, effectively slowing the max collection rate.

Create `/etc/udev/rules.d/60-ftdi_sio.rules`, with the following:
```
KERNEL=="ttyUSB[0-9]*", SUBSYSTEMS=="usb-serial", DRIVERS=="ftdi_sio", ATTR{latency_timer}="1", MODE="0666", GROUP="users"
```
The above will set the latency to 1ms (check every 1ms) and set nicer permissions for every `ftdi_sio` device. You will need to unplug and replug the usb->serial device.

#### ardu-stim

`python -m serial.tools.miniterm -e /dev/ttyACM0`
#### snippets dependencies
```
# used in some of the 'ref' scripts
pip install matplotlib
pip install vispy
pip install numpy
pip install pyglet
```
