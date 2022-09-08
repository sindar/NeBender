#!/usr/bin/env python3

import json
import os
import sys
import asyncio
import websockets
import logging
import sounddevice as sd
import argparse
import requests, time, sys, json
import subprocess

GLOBAL_LOCK = False

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    loop.call_soon_threadsafe(audio_queue.put_nowait, bytes(indata))

def infer_answer(question):
    nebender_url = "http://192.168.87.177:8008"
    headers = {
        'Content-Type': 'application/json',
    }

    body = json.dumps({'question': question})

    response = requests.post(nebender_url, headers=headers, data=body)
    if response.status_code == 200:
        # print("\nSucces, status code: " + str(response.status_code))
        data = json.loads(response.content)
        print('answer: ' + data.get('answer'))
        return data.get('answer')
        # print(data.get('answer'))
    else:
        print("\nStatus code: " + str(response.status_code) + "\nSomething went wrong. Check headers.\n")
        return None

def mic_set(val):
    exe = 'amixer -q -c 1 sset Capture ' + str(val)
    p = subprocess.Popen(["%s" % exe], shell=True, stdout=subprocess.PIPE)
    code = p.wait()

def play_tts(sentence):
    mic_set(0)
    tts_exe = 'flite -voice zk_us_bender.flitevox --setf duration_stretch=1.25 "' + sentence + '"'
    tts_proc = subprocess.Popen(["%s" % tts_exe], shell=True, stdout=subprocess.PIPE)
    code = tts_proc.wait()
    mic_set(20)

async def run_test():
    global GLOBAL_LOCK
    stop_data = False
    with sd.RawInputStream(samplerate=args.samplerate, blocksize = 4000, device=args.device, dtype='int16',
                           channels=1, callback=callback) as device:

        async with websockets.connect(args.uri) as websocket:
            await websocket.send('{ "config" : { "sample_rate" : %d } }' % (device.samplerate))

            while True:
                if not stop_data:
                    data = await audio_queue.get()
                    await websocket.send(data)
                    json_recvd = await websocket.recv()
                    recvd = json.loads(json_recvd)
                    #print (json_recvd)
                    if "result" in recvd:
                        if "text" in recvd:
                            stop_data = True
                            print("recognized: " + recvd["text"])
                            answer = infer_answer(recvd['text']) 
                            if answer != None:
                                play_tts(answer)
                                await websocket.send('{"eof" : 1}')
                                # print (await websocket.recv())
                                GLOBAL_LOCK = False
                                break

async def main():
    global args
    global loop
    global audio_queue
    global GLOBAL_LOCK

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-l', '--list-devices', action='store_true',
                        help='show list of audio devices and exit')
    args, remaining = parser.parse_known_args()
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    parser = argparse.ArgumentParser(description="ASR Server",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     parents=[parser])
    parser.add_argument('-u', '--uri', type=str, metavar='URL',
                        help='Server URL', default='ws://localhost:2700')
    parser.add_argument('-d', '--device', type=int_or_str,
                        help='input device (numeric ID or substring)')
    parser.add_argument('-r', '--samplerate', type=int, help='sampling rate', default=16000)
    args = parser.parse_args(remaining)
    loop = asyncio.get_running_loop()
    audio_queue = asyncio.Queue()

    logging.basicConfig(level=logging.INFO)
    while True:
        if not GLOBAL_LOCK:
            GLOBAL_LOCK = True
            await run_test()
            
if __name__ == '__main__':
    asyncio.run(main())
