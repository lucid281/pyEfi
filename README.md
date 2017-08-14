# PyEfi
> Tested on Debian 9, Ubuntu 16/17, Manjaro 17 -- probably ok on OSx, probably not Windows.

This is an experimental tool. No warranty expressed or implied. I am not responsible for any damages to you, people around you, or your vehicle.

## Intro

**You do not need the Megasquirt hardware to see pyEfi in action, there is code in place to 'stimulate' the pyEfi out of the box.** As a bonus, see `Fun with external data sources` if you're 1337. 

pyEfi is a set of CLI tools used to gather data from Megasquirt ECU's via the serial interface, store and publish that data via a Redis unix socket, then display and process that data in different ways.

pyEfi can collect, process and display Megasquirt data 40+ times a second for an 'A' command (100+ data points), all while keeping cpu usage under 10% on a Core2 Q6600 with other desktop apps running. It actually takes more cpu to draw the terminal

### Contact
Email me: `joshf.mobile` @ gmail.com

## Install Dependencies
- Clone the repo!
  - `git clone git@github.com:lucid281/pyEfi.git`
- Install system packages
  - `tmux` is required for pyEfi
  - `setserial` is nice to have
  - `curl` and `zlibc` are for pyenv
- Install Redis
  - Varies from distro to distro
- Install pyenv -- **pyenv is optional**, you can use the system python3 packages
  - [pyenv @ GitHub](https://github.com/pyenv/pyenv#installation)
- Install python 3.6.2
  - `pyenv install 3.6.2`
- Install pyEfi's python packages
  - `pip install -r requirements.txt`

## Configure Permissions
**Don't chmod 777 your sockets/devices, or anything, ever.** You can add your user to the `redis` group for Redis. For serial, you can add your user to `uucp` (Arch) or `dialout` (Debian) groups. If you're adding a udev rule, you can get by with the Redis entry. Logout and back in for the changes to take effect. 
```
# Example entries in /etc/group, don't copy + paste these!
uucp:x:21:usernamehere
redis:x:634:usernamehere
```

#### Udev: Serial Permissions and Latency
Older versions of the Linux kernel set `latency_timer` to `1`. The 4.x kernels I've tried set `latency_timer` to `16` by default, effectively slowing the max collection rate. You can set the default to `1` and relax the device permissions by creating a udev rule.

Create `/etc/udev/rules.d/60-ftdi_sio.rules`, with the following:
```
KERNEL=="ttyUSB[0-9]*", SUBSYSTEMS=="usb-serial", DRIVERS=="ftdi_sio", ATTR{latency_timer}="1", MODE="0660", GROUP="users"
```
The above will set the latency to 1ms (check every 1ms) and set nicer permissions for every `ftdi_sio` device. You will need to unplug and replug the usb->serial device for it to take effect.

##### Note
`low_latency` matters more for usb->serial adapters. I haven't observed any benefits on real serial ports. Also, 'real' ports collect faster (46/s vs 44/s with `A` command).

## Prepare system for Redis
#### Arch Linux:
For Arch based systems you need to make some tweaks. `systemctl status redis` should warn you if the system is not to Redis's liking. Create or append these files. Modern GNU + Linux distros should be similar.

##### /etc/sysctl.d/redis.conf 
```
vm.overcommit_memory=1
net.core.somaxconn=1024
```
##### /etc/tmpfiles.d/local.conf 
```
w /sys/kernel/mm/transparent_hugepage/enabled - - - - never
w /sys/kernel/mm/transparent_hugepage/defrag - - - - never
```

## Configure Redis Socket
The Redis Unix socket is not enabled by default. 
```
# redis conf: /etc/redis/redis.conf
# unix socket
unixsocket /var/run/redis/redis.sock
unixsocketperm 660
```
Run `systemctl start redis` to start Redis, then `systemctl enable redis` if you want Redis to start on boot. 

## Finally
At this point I usually `reboot` and make sure everything is starting in a good state. 

# Using pyEfi
###### Checklist
* Cloned the repo, dependencies installed
* Redis works and accessible by user
* Serial port accessible by user 

After cloning, installing dependencies, setting permissions and configuring Redis, `cd` to the pyEfi repo.

### CLI Intro
The CLI is pretty easy to get to get along with...
```
[user@devbox pyEfi]$ ./pyefi.py 
Type:        MainCli
String form: <__main__.MainCli object at 0x7f1bfba18c88>
File:        ~/repos/pyEfi/pyefi.py

Usage:       pyefi.py 
             pyefi.py dash
             pyefi.py run
             pyefi.py test
```
The [python fire](https://github.com/google/python-fire) module wraps everything into a cli with little effort, so I cant take any credit for this. For example, a quick and dirty way to test Redis:
```
[user@devbox pyEfi]$ ./pyefi.py test H 10000
  redis @ /var/run/redis/redis.sock
 HSET 100000 keys in 2.4052 seconds @ 41577/s
 HGET 100000 keys in 2.1674 seconds @ 46138/s
``` 
40,000 ops on single thread with no pipelining of multiple commands (Xeon E3-1232 v2), not too shabby. Start a collection process using the `microsquirt.ini` config on serial port `/dev/ttyS0`, broadcasting to `test` like this:
```
$ ./pyefi.py run collectMS microsquirt.ini /dev/ttyS0 test

pyefi collectMS | Megasquirt Serial -> Redis Collector.
  redis @ /var/run/redis/redis.sock
  ini : 115 data points in 212 bytes
  serial @ /dev/ttyS0
  pubSubKey @ stream:test

^C  [ms->redis] 46.40/s
  EXITING: KeyboardInterrupt

  PyEfiTools Runtime Summary:
    155 results @ 46.14/s in 0h 0m 3.36s .
```
`ctrl + c` will exit. You can also specify parameters explicitly, if you don't, everything needs to be in the right order...
```
$ ./pyefi.py run collectMS --iniFile microsquirt.ini --usbLoc /dev/ttyS0 --channelKey stream:1
```

### Tmuxp Intro
Out of the box, pyefi's tmuxp config (`.tmuxp.yaml`) is setup to use the 'stimulator' code to generate fake data. This mean you do not need the hardware bits to checkout the tool and see how it works.

Running `./console`  bootstraps all the required commands into a tmux 'dashboard'. Press `crtl + b` then `d` to detach and clear the sessions. You can find more about tmux around the web. 
 
Open `.tmuxp.yaml`, and it should be pretty clear what is going on. 

#### Fun with external data sources
> Here's some hints for extending the dashboard display to external sources.

Put something like this in a loop...
 ```
 eventPacket = {
 "type": "simple",
 "data": {
   "seconds": 0,
   "rpm": 625,
   etc....
   }
 }
 # below is more verbose than needs to be, but I wanted to
 # show that I obfuscate 'stream:' away from the pyefi cli.
 channelKey = 'test'
 pubKey = "stream:%s" % channelKey
 redisDb.publish(pubKey, json.dumps(eventPacket))
 ```
...create a suitable dashboards.yml...
```
dashboards:
  - name: rpm
    gaugePairs:
      1: 'rpm. .bar.0.8500.8000.>55'
      2: 'rpm.rpm.shiny.0.8500.8000.<4'
```
...sync the yml...
```
./pyefi.py dash syncYml dashboards.yml
```
...connect the dashboard to the channel. pyEfi looks under `stream:` (as mentioned above) by default...
```
./pyefi.py run dashboard --channelKey=test --confKey=rpm
```
...and you're done. Easy enough eh?

# misc
```
pyEfi
├── app
│   ├── pyefi
│   │   ├── pyEfiTools.py       # megasquirt tools
│   │   ├── retroDash.py        # data stream terminal printer
│   │   ├── pyEfiRedis.py       # redis tools
│   │   ├── pyEfiEyes.py        # data processing
│   │   ├── pyEfiStimulator.py  # simple data generator
│   │   └── ttyP.py             # quick/simple terminal printer
├── README.md
├── microsquirt.ini             # serial data structure definition
├── pyefi.py                    # cli wrapper
├── .tmuxp.yaml                 # conf to create a predefined environment
├── dashboards.yml              # dashboard configs
└── console                     # execs  .tmuxp.yaml
```
#### ardu-stim
Use python to talk to the [Ardu-stim](https://blogs.libreems.org/arduino-wheel-simulator/) serial device.

`python -m serial.tools.miniterm -e /dev/ttyACM0`
#### snippets dependencies
```
# used in some of the 'ref' scripts
pip install matplotlib
pip install vispy
pip install numpy
pip install pyglet
```
