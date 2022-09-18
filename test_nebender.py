#!/usr/bin/env python3
import json
import os
import sys
import asyncio
from tracemalloc import stop
import websockets
import logging
import sounddevice as sd
import argparse
import requests, time, sys, json
import subprocess
import soundfile as sf

MIC_GAIN = 20

def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    loop.call_soon_threadsafe(audio_queue.put_nowait, bytes(indata))

def infer_answer(question):
    nebender_url = "http://192.168.89.177:8008"
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

def read_subscription_key():
    service_region = "northeurope"

    try:
        with open('model/subscription-'+ service_region + '.key') as key_file:
                subscription_key = key_file.read().rstrip('\n\r')
    except:
        print("Error reading subscription key file!")
        exit(1)

    if subscription_key is None:
        print("Subscription key is empty!")
        exit(1)

    return subscription_key

def get_token(subscription_key):
    fetch_token_url = 'https://northeurope.api.cognitive.microsoft.com/sts/v1.0/issueToken'
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key
    }
    response = requests.post(fetch_token_url, headers=headers)
    access_token = str(response.text)
    print("Access token: " + access_token)
    return access_token

def play_wav(path):
    aplay_exe = 'aplay -Dplug:default ' + str(path)
    play_proc = subprocess.Popen(["%s" % aplay_exe], shell=True, stdout=subprocess.PIPE)
    play_proc.wait()

def record_wav():
    arecord_exe = 'arecord -c 2 -f S16_LE -d 4 -Dhw:1 /dev/shm/record.wav'
    rec_proc = subprocess.Popen(["%s" % arecord_exe], shell=True, stdout=subprocess.PIPE)
    rec_proc.wait()

def azure_tts(sentence):
    global subscription_key
    global access_token

    constructed_url = "https://northeurope.voice.speech.microsoft.com/cognitiveservices/v1?deploymentId=c418a752-7ca8-4f0d-9d4c-a17d59dd9a98"
    headers = {
        'Authorization': 'Bearer ' + str(access_token),
        'Content-Type': 'application/ssml+xml',
        'X-Microsoft-OutputFormat': 'riff-16khz-16bit-mono-pcm',
        'User-Agent': 'Bender'
    }

    body = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" \
        xmlns:mstts=\"http://www.w3.org/2001/mstts\" \
        xml:lang=\"en-US\"><voice name=\"Bender\">"\
        + sentence + "</voice></speak>"   

    response = requests.post(constructed_url, headers=headers, data=body)
    if response.status_code == 200:
        # wav_path = '/dev/shm/tts.wav'
        wav_path = '/home/sindar/mnt/tts.wav'
        with open(wav_path, 'wb') as audio:
            audio.write(response.content)
            # play_wav('/dev/shm/tts.wav')
            f = sf.SoundFile(wav_path)
            delay = (len(f) / f.samplerate)
            time.sleep(delay + 1) #подождём пока проиграется файл
            # print("\nStatus code: " + str(response.status_code) + "\nYour TTS is ready for playback.\n")
    else:
        print("\nStatus code: " + str(response.status_code) + "\nSomething went wrong. Check your subscription key and headers.\n")

def flite_tts(sentence):
    mic_set(0)
    tts_exe = 'flite -voice ./model/zk_us_bender.flitevox --setf duration_stretch=1.25 "' + sentence + '"'
    tts_proc = subprocess.Popen(["%s" % tts_exe], shell=True, stdout=subprocess.PIPE)
    code = tts_proc.wait()
    mic_set(MIC_GAIN)

def get_kw(speech_rec_proc):
    print("get kw: ")
    retcode = speech_rec_proc.returncode
    utt = speech_rec_proc.stdout.readline().decode('utf8').rstrip().lower()
    print('kw = ' + utt)
    return utt

def stop_proc(pid):
    stop_exe = 'kill -s STOP ' + str(pid)
    p = subprocess.Popen(["%s" % stop_exe], shell=True, stdout=subprocess.PIPE)
    code = p.wait()

def cont_proc(pid):
    cont_exe = 'kill -s CONT ' + str(pid)
    p = subprocess.Popen(["%s" % cont_exe], shell=True, stdout=subprocess.PIPE)
    code = p.wait()

async def vosk_recognize_mic(uri, wake_word_pid):
    # stop_proc(wake_word_pid)
    print('vosk recognize: ')
    samplerate = 16000
    device = 12
    with sd.RawInputStream(samplerate=samplerate, blocksize = 4000, device=device, dtype='int16',
                           channels=1, callback=callback) as device:

        async with websockets.connect(uri) as websocket:
            await websocket.send('{ "config" : { "sample_rate" : %d } }' % (device.samplerate))

            while True:
                data = await audio_queue.get()
                await websocket.send(data)
                json_recvd = await websocket.recv()
                recvd = json.loads(json_recvd)
                #print (json_recvd)
                if "result" in recvd:
                    if "text" in recvd:
                        print("recognized: " + recvd["text"])
                        answer = infer_answer(recvd['text']) 
                        if answer != None:
                            # flite_tts(answer)
                            azure_tts(answer)
                            await websocket.send('{"eof" : 1}')
                            # print (await websocket.recv())
                            break
    # cont_proc(wake_word_pid)

async def vosk_recognize_file(uri):
    async with websockets.connect(uri) as websocket:

        proc = await asyncio.create_subprocess_exec(
                       'ffmpeg', '-nostdin', '-loglevel', 'quiet', '-i', "/dev/shm/record.wav",
                       '-ar', '16000', '-ac', '1', '-f', 's16le', '-',
                       stdout=asyncio.subprocess.PIPE)

        await websocket.send('{ "config" : { "sample_rate" : 16000 } }')

        while True:
            data = await proc.stdout.read(8000)

            if len(data) == 0:
                break

            await websocket.send(data)
            json_recvd = await websocket.recv()
            recvd = json.loads(json_recvd)
            #print (json_recvd)
            if "result" in recvd:
                if "text" in recvd:
                    print("recognized: " + recvd["text"])
                    answer = infer_answer(recvd['text']) 
                    if answer != None:
                        # flite_tts(answer)
                        mic_set(0)
                        azure_tts(answer)
                        mic_set(MIC_GAIN)
                        await websocket.send('{"eof" : 1}')
                        # print (await websocket.recv())
                        break
            # print (await websocket.recv())

        await websocket.send('{"eof" : 1}')
        # print (await websocket.recv())

        await proc.wait()

import azure.cognitiveservices.speech as speechsdk

async def azure_stt(subscription_key):
    # subscription_key = read_subscription_key()
    speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region="northeurope")
    speech_config.speech_recognition_language="en-US"

    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    print("Speak into your microphone.")
    speech_recognition_result = speech_recognizer.recognize_once_async().get()

    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print("Recognized: {}".format(speech_recognition_result.text))
        return speech_recognition_result.text
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
            print("Did you set the speech resource key and region values?")

async def main():
    global loop
    global audio_queue
    global subscription_key
    global access_token

    loop = asyncio.get_running_loop()
    audio_queue = asyncio.Queue()

    # wake_word_cmd = 'pocketsphinx_continuous  -dictcase yes -inmic yes  -ds 3 -samprate 8000  -hmm /home/pi/pRodriguezAssistant/common/resources/en/cmusphinx-en-us-ptm-8khz-5.2/ -dict /home/pi/pRodriguezAssistant/profiles/bender/resources/en/bender.dic -keyphrase "bender" -kws_threshold 1e-3 -logfn /dev/null'

    # wake_word_proc = subprocess.Popen(["%s" % wake_word_cmd], shell=True, stdout=subprocess.PIPE)
    # print(["%s" % wake_word_cmd])
    # time.sleep(5)

    # wake_word_pid = wake_word_proc.pid + 1

    subscription_key = read_subscription_key()
    access_token = get_token(subscription_key)

    while True:
        # Azure STT works only on x86
        try:
            utt = await azure_stt(subscription_key)
            mic_set(0)
            answer = infer_answer(utt)
            if answer != None:
                azure_tts(answer)
                # flite_tts(answer)
        except:
            print("got exception")
        finally:
            mic_set(MIC_GAIN)

        # if 'bender' in get_kw(wake_word_proc):
        #     # await vosk_recognize_mic('ws://192.168.87.177:2700', wake_word_pid)
        #     record_wav()

        # print("start recording")    
        # record_wav()
        # print("finish recording")
        # await vosk_recognize_file('ws://192.168.87.177:2700')

if __name__ == '__main__':
    asyncio.run(main())
