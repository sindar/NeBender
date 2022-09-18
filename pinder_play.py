#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import subprocess

WAV_PATH = '/dev/shm/tts.wav'
NEOPIX_RUN = "/home/pi/nebender/ledstrip-neopixel.py"

while(True):
    if os.path.exists(WAV_PATH):
        aplay_exe = 'aplay -Dplug:default ' + WAV_PATH
        aplay_proc = subprocess.Popen(["%s" % aplay_exe], shell=True, stdout=subprocess.PIPE)
        talk_proc = subprocess.Popen(NEOPIX_RUN + " -s talk", shell=True)
        time.sleep(1)
        os.remove(WAV_PATH)
        aplay_proc.wait()
        talk_proc.kill()
        kill_exe = 'kill ' + str(talk_proc.pid + 2)
        p = subprocess.Popen(["%s" % kill_exe], shell=True, stdout=subprocess.PIPE)
        p.wait()
        kill_exe = 'kill ' + str(talk_proc.pid + 1)
        p = subprocess.Popen(["%s" % kill_exe], shell=True, stdout=subprocess.PIPE)
        p.wait()
        subprocess.Popen(NEOPIX_RUN + " -s off", shell=True)
    time.sleep(1)