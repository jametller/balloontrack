from io import StringIO
from flask import Flask
import json
import os
import threading
import time
from shutil import copyfile
import serial
import demo_kml

coordinate = 1
serial_balloon = None
last_balloon_time = None
last_balloon_coord = None
last_car_coord = '-0.565570,41.540143,500.0'
ascend_rate = 0.0
demo_mode = True

def addCoordinateToKml(coordinate, kml):
    kmldata = ""
    #TODO: Edit file instead of read/remove/write
    with open(kml, 'r') as f:
        data = f.read() 
        startpos = data.find('</coordinates>')
        kmldata = data[:startpos-1]
        kmldata += coordinate + "\n\n"
        kmldata += data[startpos:]
    try:
        os.remove(kml)
    except:
        app.logger.warning("Error removing file")
    return kmldata

def addLineToTarget(sourceCoordinate, targetCoordinate, kmlData):
    startpos = kmlData.find('<coordinates>')
    startpos = kmlData.find('<coordinates>',startpos + 2)
    ending = kmlData.find('</coordinates>')
    ending = kmlData.find('</coordinates>', ending + 2)
    tail = kmlData[ending:]
    kmlData = kmlData[:startpos+len('<coordinates>')]
    kmlData += "\n" + sourceCoordinate + "\n" + targetCoordinate + "\n" + tail
    return kmlData

def update_ascend_date(coord, t):
    global ascend_rate
    if coord != None and last_balloon_coord != None:
        alt = float(coord.split(',')[2])
        last_alt = float(last_balloon_coord.split(',')[2])
        ascend_rate = (alt - last_alt) / (t - last_balloon_time)
        print('ascend rate ' + str(ascend_rate))

def is_good_data (coord):
    try:
        c = coord.split(',')
        t = float(c[0])
        t = float(c[1])
        t = float(c[2])
    except:
        return False
    return True

def log_data (data):
    os.system('/bin/echo ' + data + '>>raw.log')

def getBalloonCoordinates():
    global coordinate
    global last_balloon_coord
    global last_balloon_time
    while True:
        try:
            if demo_mode:
                time.sleep(2.0)
                coords = demo_kml.get_next_demo_coord()
            else:
                coords = serial_car.readline()
                coords = coords.decode('utf-8').rstrip()
            if is_good_data(coords):
                now = time.time()
                log_data(str(now) + "," + time.ctime(now) + "," + coords)
                update_ascend_date (coords, now)
                last_balloon_time = now
                last_balloon_coord = coords
                #if kml does not exist, create from template
                if not os.path.isfile('static/prova.kml'):
                    copyfile('static/template.kml', 'static/prova.kml')
                #add coordinate to KML
                kmldata = addCoordinateToKml(last_balloon_coord,'static/prova.kml')
                coordinate += 1
                kmldata = addLineToTarget(last_car_coord, last_balloon_coord, kmldata)
                #write file
                with open('static/prova.kml','w') as f:
                    f.write(kmldata)
            else:
                print('discarding data: ' + str(coords))
        except Exception as e:
            print('error receiving from balloon serial: ', e)
            time.sleep(2.0)

def initSerial(serialport):
    try:
        ser = serial.Serial(
        port=serialport,\
        baudrate=19200,\
        parity=serial.PARITY_NONE,\
        stopbits=serial.STOPBITS_ONE,\
        bytesize=serial.EIGHTBITS,\
            timeout=5)
    except:
        return None
    return ser

app = Flask(__name__,
            static_url_path='', 
            static_folder='static',
            template_folder='templates')


if not demo_mode:
    print('Initializing serial port /dev/ttyUSB0')
    while (serial_car := initSerial('/dev/ttyUSB0')) == None:
        time.sleep(2.0)
        app.logger.warning('Waiting serial port /dev/ttyUSB0')

if input('Remove old kmls? (y/n)') == 'y':
    try:
        os.remove('static/prova.kml')
        os.remove('static/cotxe.kml')
    except:
        app.logger.warning("Error removing file")

t1 = threading.Thread(target = getBalloonCoordinates)
t1.start()

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/balloonData")
def balloon_pos():
    return json.dumps({"ascend_rate": str(round(ascend_rate,3)), "position": str(last_balloon_coord), "altitude": str(last_balloon_coord.split(',')[2])})

@app.route("/carPosition")
def car_pos():
    return last_car_coord
