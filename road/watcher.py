import sys, time, threading, serial
from mbee import serialstar
from data_classes import *
from lib.lsm6ds3 import *


#-------------------------------------------------------------------------------------#

class Writer(threading.Thread):
    def __init__(self, out=''):
        super().__init__()
        self._out = out

    @property
    def out(self):
        return self._out

    @out.setter
    def out(self, string):
        self._out = string

    def run(self):
        t = threading.currentThread()
        while getattr(t, "do_run", True):
            sys.stdout.write(self._out)
            sys.stdout.flush()
            time.sleep(0.2)

#-------------------------------------------------------------------------------------#
""" Used to control the motor by Motor_controller class """
class Motor_thread(threading.Thread):
    def __init__(self, lock, controller):
        super().__init__()
        self.lock = lock
        self.paused = False
        self.controller = controller

    def run(self):
        th = threading.currentThread()
        while getattr(th, "do_run", True):
            # FIXME: MOTOR
            # self.controller.packageResolver()
            with self.lock:
                if self.lock.acquire(False):
                    self.controller.control()

#-------------------------------------------------------------------------------------#
""" Used to control all operations """
class Watcher(threading.Thread):
    def __init__(self, lock, motor_thread, writer, serial_device, accel, classes):
        super().__init__()
        self.lock = lock
        self.motor_thread = motor_thread
        self.writer = writer
        self.dev = serial_device
        self.accel = accel
        self.mbee = serialstar.SerialStar('/dev/ttyS2', 9600)

        self.mbee.callback_registring("81", self.frame_81_received)

        self.hostData = classes[0]
        self.roadData = classes[1]
        self.specialData = classes[2]

    def run(self):
        stringData = 't:\t{:.2f}\tv:\t{:.2f}\tB1:\t{:.2f}\tB2:\t{:.2f}\tmode:\t{}\tL:\t{:.3f}\t\t{:s}\n'

        th = threading.currentThread()
        while getattr(th, "do_run", True):

            # data = serial_recv(self.dev, 60)
            # self.motor_thread.controller.data = data
            # self.motor_thread.controller.data = [self.hostData, self.roadData, self.specialData]

            # Getting MBee data
            with self.lock:
                if self.lock.acquire(False):
                    self.mbee.run()
            #
            with self.lock:
                if self.lock.acquire(False):
                    self.motor_thread.controller.update_host_to_road()

            # Check accelerometer data
            [x, y, z] = self.accel.getdata()
            thr = 5
            if (x > thr) or (z > thr):
                self.motor_thread.controller.HARD_STOP = 1
                print('got')
                print(x," ", y," ", z)

            data = (0,0,0,0,0,0,'')
            with self.lock:
                if self.lock.acquire(False):
                    data = self.motor_thread.controller.get_data()
            # data = (self.motor_thread.controller.t, self.motor_thread.controller.speed, self.roadData.base1, self.roadData.base2,
            #         self.roadData.mode, self.roadData.coordinate, tmp)
            self.writer.out = stringData.format(*data)


    #   Callback functions for SerialStar
    def frame_81_received(packet):
        print("Received 81-frame.")
        print(packet)



#-------------------------------------------------------------------------------------#
#   Serial communication
def serial_init(speed=9600, port='/dev/ttyS2'):
    try:
        dev = serial.Serial(
        port=port,
        baudrate=speed,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=0.1
    )
    except serial.serialutil.SerialException:
        dev = None

    return dev

def serial_recv(dev, size):
    string = dev.read(size).decode()
    return string

def serial_send(dev, string):
    dev.write(string.encode('utf-8'))
