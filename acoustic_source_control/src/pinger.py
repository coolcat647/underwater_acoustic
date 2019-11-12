#!/usr/bin/env python

import rospy
import rospkg
import os
import sys
import time
import signal
import subprocess
from std_srvs.srv import Trigger, TriggerResponse

# Import GPIO package for Rpi3 relay control
if 'arm' in os.uname()[-1]:
    import RPi.GPIO as GPIO
    GPIO.setwarnings(False) 
    GPIO.setmode(GPIO.BOARD)
    GPIO_PIN_RELAY = 7
    GPIO.setup(GPIO_PIN_RELAY, GPIO.OUT, initial = GPIO.LOW)

COLOR_NC='\033[0m'
COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'

class PingerNode(object):
    def __init__(self, node_name, duration_ms=50, sound_freq=15000, play_freq=0.5):
        self.pack_path = rospkg.RosPack().get_path('acoustic_source_control')
        self.cmd = ''
        self.process = None             # declare for playsound process handler
        self.is_rpi = 'arm' in os.uname()[-1]
        self.is_busy = False

        # Declare pinger parameters with default setting, then import the user setting if they were existed
        self.duration_ms = rospy.get_param('~duration_ms', duration_ms)
        self.sound_freq = rospy.get_param('~sound_freq', sound_freq)
        self.play_freq = rospy.get_param('~play_freq', play_freq)

        # For Rpi3 relay control -> turn on amplifier
        if self.is_rpi: 
            GPIO.output(GPIO_PIN_RELAY, GPIO.HIGH) 

        # ROS service
        self.srv = rospy.Service(node_name, Trigger, self.sound_cb)

        rospy.on_shutdown(self.onShutdown)
        rospy.loginfo('{}{} is waiting for request{}'.format(COLOR_GREEN, rospy.get_name(), COLOR_NC))


    # Service handler
    def sound_cb(self, req):
        try:
            '''
                If there is any old process existed when you call the service,
                send the signal to kill the process first.
            '''
            if self.process != None:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)    
                rospy.loginfo("stop %s " % rospy.get_name()) 
                self.process = None   

            # The pinger will just play one time in one_shot mode
            self.cmd = 'python %s/src/sine_generator.py %s %s %s 0' % \
                (self.pack_path, self.duration_ms, self.sound_freq, self.play_freq)

            if not self.is_busy:
                self.is_busy = True
                rospy.loginfo("Output freqency of %s = %d Hz with %d ms and %d ms silence" % \
                    (rospy.get_name(), self.sound_freq, self.duration_ms, 1000 / self.play_freq - self.duration_ms))
                
                # Open the subprocess
                self.process = subprocess.Popen(self.cmd, stdout= subprocess.PIPE, shell=True, preexec_fn=os.setsid)
                return TriggerResponse(message='{} turn on.'.format(rospy.get_name()))

        except OSError as e:
            print "OSError > ", e.errno
            print "OSError > ", e.strerror
            print "OSError > ", e.filename
            exit(-1)
        except:
            print "Error > ",sys.exc_info()[0]
            exit(-1)
        return TriggerResponse(message='{} stop...'.format(rospy.get_name()))

    def onShutdown(self):
        # This program must get here after killing the ROS node
        if self.process != None:
            os.killpg(os.getpgid(pinger.process.pid), signal.SIGTERM)
            rospy.loginfo('[%s] stop...' % rospy.get_name()) 
            del self.process
        if hasattr(self, 'is_rpi') and self.is_rpi:
            GPIO.output(GPIO_PIN_RELAY, GPIO.LOW)    # Just turn off the relay for safety reason
        rospy.loginfo('[%s] Shutdown.' % rospy.get_name())


if __name__ == "__main__":
    if sys.argv[1].find('pinger_num=') != -1:
        pinger_num = sys.argv[1].split('=')[1]
    else: 
        print COLOR_GREEN + 'Pinger number has not be assigned' + COLOR_NC
        exit(-1)
    node_name = 'pinger' + pinger_num
    rospy.init_node(node_name, anonymous = False)
    pinger = PingerNode(node_name = node_name)
    rospy.spin()

    
