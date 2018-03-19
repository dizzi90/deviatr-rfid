#!/usr/bin/env python
# -*- coding: utf8 -*-

import MFRC522
import signal
import time
import picamera
import base64
import requests
import json
import RPi.GPIO as GPIO
from subprocess import call

continue_reading = True


def end_read(signal, frame):
    global continue_reading
    print('Ctrl+C captured, ending read.')
    continue_reading = False
    GPIO.cleanup()


def Celebrate():
    Say('Iotkonge')
    Say('Marius')
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(3, GPIO.OUT)
    pwm = GPIO.PWM(3, 50)
    pwm.start(0)

    def SetAngle(angle):
        duty = angle / 18 + 2
        GPIO.output(3, True)
        pwm.ChangeDutyCycle(duty)
        time.sleep(1)
        GPIO.output(3, False)
        pwm.ChangeDutyCycle(0)
    SetAngle(40)
    pwm.stop()
    GPIO.cleanup()


def PositiveFeedback(event, identity=False):
    if event == 'GOOD_SCAN_SSCC':
        Say('Beep')
        Say('Takk')
        Say('Choosedeviate')
        print('good sscc scan')
        return True
    if event == 'GOOD_EVENT_ID':
        Say('Standaside')
        print('good event id scan')
        return True
    if event == 'GOOD_CARD_SCAN':
        Say('Takk')
        Say('Scanbarcode')
        print('good card scan')
        return True
    if event == 'GOOD_PICTURE':
        Say('Klikk')
        time.sleep(1)
    if event == 'GOOD_SUBMISSION':
        Say('Takkforviktigbidrag')
        if identity:
            name_sounds = ['Jonny', 'Magnus']
            id_resp = json.loads(identity.text)
            first_name = str(id_resp['Name']).split()[0]

            if first_name in name_sounds:
                Say(first_name)
            else:
                if first_name == 'Marius':
                    Celebrate()
                else:
                    Say('Dollarfornavn')

        return True

    return True


def EventId(UID):
    event = str(raw_input('scan event id\n'))
    r = requests.post('http://coopw10:9004/event',
                      json={'eventid': event, 'uid': UID})
    print('Eventid API said:' + r.text)
    if str(r.text) == 'true':
        return event
    NegativeFeedback()
    return False


def NegativeFeedback():
    print('Bad doser.\n')


def ValidateSscc(sscc):
    if sscc.startswith('0037') and len(sscc) == 20:
        return True
    else:
        return False


def ScanSSCC():
    """Scan pallet barcode."""
    SSCC = str(input('scan\n'))
    if ValidateSscc(SSCC):
        return SSCC
    NegativeFeedback()


def takePicture():
    with picamera.PiCamera() as camera:
        camera.resolution = (1024, 768)
        camera.start_preview()
        # Camera warm-up time
        print('Taking picture\n')
        time.sleep(2)
        camera.capture('foo.jpg')
        image = base64.encodestring(open('foo.jpg', 'rb').read())
        return image


def Say(filename):
    # subprocess.call(["sudo","omxplayer","-o","local","/home/pi/deviatr/sounds/Takk.mp3"])
    response = call(['sudo', 'omxplayer', '-o', 'local',
                     '../sounds/' + filename + '.mp3'])
    print('called audio')
    if response:
        print(response)
        return True


def ReadConfig():
    with open('deviatr.conf') as file:
        data = file.read()
        return data


def Identify(employee, uid):
    try:
        r = requests.post(url='http://coopw10:9004/identify',
                          json={'employeeNumber': ConcatenateEmployeeId(employee), 'uid': str(uid)})
    except requests.exceptions.RequestException as e:
        print(e)
        raise error
    if r.status_code == 200:
        return r


def Submit(deviation, filename):
    filename = 'foo.jpg'
    files = {'file': open(filename, 'rb')}
    r = requests.post(url='http://coopw10:9004/deviate',
                      json=deviation)
    if r.status_code == 200:
        return True
    NegativeFeedback()


def ConcatenateEmployeeId(list):
    ''' Returns single string '''
    return str(list[0]) + str(list[1]) + str(list[2]) + str(list[3])


def GetUid():
    # with open('deviatr.uid') as file:
    return '1'  # file.read().replace('\n', '')


def mainLoop(uid):
    '''main loop.'''
    signal.signal(signal.SIGINT, end_read)
    MIFAREReader = MFRC522.MFRC522()
    (status, TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)
    if status == MIFAREReader.MI_OK:
        (status, employee) = MIFAREReader.MFRC522_Anticoll()
        if status == MIFAREReader.MI_OK:
            identity = Identify(employee, uid)
            if identity.status_code == 200:
                identity.encoding = 'utf-8'
                PositiveFeedback('GOOD_CARD_SCAN')
                sscc = ScanSSCC()
                if sscc:
                    PositiveFeedback('GOOD_SCAN_SSCC')
                    event = EventId(uid)
                    if event in ['1', '2', '3']:
                        PositiveFeedback('GOOD_EVENT_ID')
                        pic = takePicture()
                        if pic:
                            PositiveFeedback('GOOD_PICTURE')
                            employee = ConcatenateEmployeeId(employee)
                            deviation = {'sscc': sscc,
                                         'employee': employee,
                                         'uid': uid,
                                         'eventid': event}
                            submission = Submit(deviation, 'foo.jpg')
                            if submission:
                                PositiveFeedback('GOOD_SUBMISSION', identity)
                                return None


print('You devious!')

while continue_reading:
    UID = GetUid()
    mainLoop(UID)
    GPIO.cleanup()
