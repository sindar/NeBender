#!/usr/bin/env python
# -*- coding: utf-8 -*-

import board
import neopixel
import sys
import getopt
import time
import random

pixels_pin = board.D12

pixels_num = 40
ORDER = neopixel.GRB

default_color = (255, 255, 0)
no_color = (0, 0, 0)

def switch_pixels(pixels, on, color):
    if on:
        pixels.fill(color)
    else:
        pixels.fill((0, 0, 0))
    pixels.show()

def music(pixels, num):
    while True:
        for i in range(num):
            r = random.randrange(255)
            g = random.randrange(255)
            b = random.randrange(255)
            pixels[i] = (r, g, b)
        pixels.show()
        time.sleep(0.5)

def talk(pixels, pin, mode = 'normal', timeout = 300):
    # if mode == 'plugged_in':
    #     back_color = darkorange
    #     front_color = blue
    #     period = 0.1
    # elif mode == 'xmas':
    #     back_color = blue
    #     front_color = red
    #     period = 0.2
    # else:
    #     back_color = no_color
    #     front_color = default_color
    #     period = 0.25

    back_color = no_color
    front_color = default_color
    period = 0.25

    t = 0
    while t < timeout: # maximum answer length to prevent infinite loop
        fill_range(pixels, pin, 6, 12, front_color, back_color)
        time.sleep(period)

        fill_range(pixels, pin, 2, 4, front_color, back_color)
        fill_range(pixels, pin, 6, 8, front_color)
        fill_range(pixels, pin, 10, 12, front_color)
        fill_range(pixels, pin, 14, 16, front_color)
        time.sleep(period)

        fill_range(pixels, pin, 6, 12, front_color, back_color)
        time.sleep(period)

        fill_range(pixels, pin, 1, 5, front_color, back_color)
        fill_range(pixels, pin, 6, 7, front_color)
        fill_range(pixels, pin, 11, 12, front_color)
        fill_range(pixels, pin, 13, 17, front_color)
        time.sleep(period)
        t += period * 4

def fill_range(pixels, pin, start, end, front_color, back_color = None):
    if back_color:
        pixels.fill(back_color)
    for i in range(start, end):
        pixels[i] = front_color
    pixels.show()

def main(argv):
    #print ('Argument List:', str(sys.argv))
    pixels = None
    on = False
    music_on = False
    talk_on = False
    red = default_color[0]
    green = default_color[1]
    blue = default_color[2]
    help_message = 'backlight.py -s <on|off|talk|music> -r <val> -g <val> -b <val>' 
    if len(argv) < 2:
        print (help_message)
    try:
        opts, args = getopt.getopt(argv, "hs:r:g:b:", ["switch=", "red=", "green=", "blue="])
    except getopt.GetoptError:
        print (help_message)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print (help_message)
            sys.exit(0)
        elif opt in ("-s", "--switch"):
            pixels = neopixel.NeoPixel(pixels_pin, pixels_num, brightness=0.5, auto_write=False,
                                       pixel_order=ORDER)
            if (arg == 'on'):
                on = True
            elif (arg == 'talk'):
                talk_on = True
            elif (arg == 'music'):
                music_on = True
        elif opt in ("-r", "--red"):
            red = int(arg)
        elif opt in ("-g", "--green"):
            green = int(arg)
        elif opt in ("-b", "--blue"):
            blue = int(arg)

    if (pixels):
        switch_pixels(pixels, on, (red, green, blue))

    if (talk_on):
        talk(pixels, pixels_pin)

    if (music_on):
        music(pixels, num)

if __name__ == "__main__":
   main(sys.argv[1:])
