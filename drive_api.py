import argparse
import tornado.ioloop
import tornado.web
from datetime import datetime
import os
from operator import itemgetter
import RPi.GPIO as GPIO
import requests
from time import sleep

class PostHandler(tornado.web.RequestHandler):

    # I don't understand decorators, but this fixed my "can't set attribute" error
    @property
    def settings(self):
         return self._settings

    @settings.setter
    def settings(self,settings):
        self._settings = settings

    def initialize(self, settings):
        self.settings = settings

    def post(self):
        timestamp = datetime.now()
        data_json = tornado.escape.json_decode(self.request.body)
        allowed_commands = set(['37','38','39','40'])
        command = data_json['command']
        command = list(command.keys())
        command = set(command)
        command = allowed_commands & command
        file_path = str(os.path.dirname(os.path.realpath(__file__)))+"/data/session.txt"
        log_entry = str(command)+" "+str(timestamp)
        log_entries.append((command,timestamp))
        with open(file_path,"a") as writer:
            writer.write(log_entry+"\n")
        print(log_entry)
        speed = self.settings['speed']
        if '37' in command:
            motor.forward_left(speed)
        elif '38' in command:
            motor.forward(speed)
        elif '39' in command:
            motor.forward_right(speed)
        elif '40' in command:
            motor.backward(100)
        else:
            motor.stop()
        
# This only works on data from the same live python process. It doesn't 
# read from the session.txt file. It only sorts data from the active
# python process. This is required because it reads from a list instead
# of a file  on data from the same live python process. It doesn't 
# read from the session.txt file. It only sorts data from the active
# log_entries python list
class StoreLogEntriesHandler(tornado.web.RequestHandler):
    def get(self):
        file_path = str(os.path.dirname(os.path.realpath(__file__)))+"/data/clean_session.txt"
        sorted_log_entries = sorted(log_entries,key=itemgetter(1))
        prev_command = set()
        allowed_commands = set(['38','37','39','40'])
        for log_entry in sorted_log_entries:
            command = log_entry[0]
            timestamp = log_entry[1]
            if len(command ^ prev_command) > 0:
                prev_command = command
                with open(file_path,"a") as writer:
                    readable_command = []
                    for element in list(command):
                        if element == '37':
                            readable_command.append("left")
                        if element == '38':
                            readable_command.append("up")
                        if element == '39':
                            readable_command.append("right")
                        if element == '40':
                            readable_command.append("down")
                    log_entry = str(list(readable_command))+" "+str(timestamp)
                    writer.write(log_entry+"\n")
                print(log_entry)
        self.write("Finished")
   
class MultipleKeysHandler(tornado.web.RequestHandler):

    def get(self):
        print("HelloWorld")
        self.write('''
                <!DOCTYPE html>
                <html>
                    <head>
                        <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.12.2/jquery.min.js"></script>
                        <script>
                            var keys = {};

                            $(document).keydown(function (e) {
                                keys[e.which] = true;
                                
                                var json_upload = JSON.stringify({command:keys});
                                var xmlhttp = new XMLHttpRequest(); 
                                xmlhttp.open("POST", "/post");
                                xmlhttp.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
                                xmlhttp.send(json_upload);

                                printKeys();
                            });

                            $(document).keyup(function (e) {
                                delete keys[e.which];
                                
                                var json_upload = JSON.stringify({command:keys});
                                var xmlhttp = new XMLHttpRequest(); 
                                xmlhttp.open("POST", "/post");
                                xmlhttp.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
                                xmlhttp.send(json_upload);

                                printKeys();
                            });

                            function printKeys() {
                                var html = '';
                                for (var i in keys) {
                                    if (!keys.hasOwnProperty(i)) continue;
                                    html += '<p>' + i + '</p>';
                                }
                                $('#out').html(html);
                            }

                        </script>
                    </head>
                    <body>
                        Click in this frame, then try holding down some keys
                        <div id="out"></div>
                    </body>
                </html>
            ''')


class Motor:

     def __init__(self, pinSpeed, pinDirection, pinSteering):

        self.pinSpeed = pinSpeed
        self.pinDirection = pinDirection
        self.pinSteering = pinSteering

        GPIO.setup(self.pinSpeed, GPIO.OUT)
        GPIO.setup(self.pinDirection, GPIO.OUT)
        GPIO.setup(self.pinSteering, GPIO.OUT)

        self.pwm_speed = GPIO.PWM(self.pinSpeed, 100)
        self.pwm_speed.start(0)
        self.pwm_steering = GPIO.PWM(self.pinSteering, 50)
        self.pwm_steering.start(7.25)

     def forward(self, speed):

        GPIO.output(self.pinDirection, False)
        self.pwm_speed.ChangeDutyCycle(speed)    
        self.pwm_steering.ChangeDutyCycle(7.25)

     def forward_left(self, speed):

        GPIO.output(self.pinDirection, False)
        self.pwm_speed.ChangeDutyCycle(speed)
        self.pwm_steering.ChangeDutyCycle(10)

     def forward_right(self, speed):

        GPIO.output(self.pinDirection, False)
        self.pwm_speed.ChangeDutyCycle(speed)
        self.pwm_steering.ChangeDutyCycle(5)

     def backward(self, speed):

        self.pwm_speed.ChangeDutyCycle(20)
        GPIO.output(self.pinDirection, True)
        self.pwm_steering.ChangeDutyCycle(7.25)

     def left(self, speed):

        self.pwm_speed.ChangeDutyCycle(0)
        self.pwm_steering.ChangeDutyCycle(10)

     def right(self, speed):

        self.pwm_speed.ChangeDutyCycle(0)
        self.pwm_steering.ChangeDutyCycle(5)

     def stop(self):

        self.pwm_speed.ChangeDutyCycle(0)
        self.pwm_steering.ChangeDutyCycle(7.5)

def make_app(settings):
    return tornado.web.Application([
        (r"/drive",MultipleKeysHandler),(r"/post", PostHandler, {'settings':settings}),
        (r"/StoreLogEntries",StoreLogEntriesHandler)
    ])

if __name__ == "__main__":

    # Parse CLI args
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--speed_percent", required=True, help="Between 0 and 100")
    args = vars(ap.parse_args())
    GPIO.setmode(GPIO.BOARD)
    motor = Motor(13, 15, 3)
    log_entries = []
    settings = {'speed':float(args['speed_percent'])}
    app = make_app(settings)
    app.listen(81)
    tornado.ioloop.IOLoop.current().start()
