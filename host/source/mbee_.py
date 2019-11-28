import sys, os, subprocess, time
import struct
import binascii
import global_
import threading
from PyQt5.QtCore import QThread, QMutex

from mbee import serialstar
from lib.data_classes import *

TX_ADDR = '0002'


def frame_81_received(package):
    data = decrypt_package(package['DATA'])
    print('here')
    if isinstance(data, RTHData):
        global_.mutex.tryLock(timeout=10)
        global_.roadData = data
        update_road_to_host()
        global_.mutex.unlock()
    # print("Received 81-frame.")
    # print(package)
    pass

def frame_83_received(package):
    # print("Received 83-frame.")
    # print(package)
    pass

def frame_87_received(package):
    # print("Received 87-frame.")
    # print(package)
    pass

def frame_88_received(package):
    # print("Received 88-frame.")
    # print(package)
    pass

def frame_89_received(package):
    # print("Received 89-frame.")
    # print(package)
    pass

def frame_8A_received(package):
    # print("Received 8A-frame.")
    # print(package)
    pass

def frame_8B_received(package):
    # print("Received 8B-frame.")
    # print(package)
    pass

def frame_8C_received(package):
    # print("Received 8C-frame.")
    # print(package)
    pass

def frame_8F_received(package):
    # if (package['SOURCE_ADDRESS_HEX'] == TX_ADDR):
    #     rssi = package['RSSI']
    #     global_.roadData.RSSI = rssi
    # print("Received 8F-frame.")
    # print(package)
    pass

def frame_97_received(package):
    # print("Received 97-frame.")
    # print(package)
    pass


def update_road_to_host():
    global_.roadData.RSSI_signal.emit(global_.roadData.RSSI)
    global_.hostData.mode = global_.roadData.mode
    global_.hostData.direction = global_.roadData.direction
    pass


#----------------------------------------------------------------------------------------------#
#   A thread used to operate with MBee.
class MbeeThread(QThread):
    def __init__(self, port='/dev/ttySAC4', baudrate=19200):
        QThread.__init__(self)
        self.alive = True
        self.t = 0
        self.t_prev = 0

        # subprocess.call('./radio_off.sh')
        # subprocess.call('./radio_on.sh')

        self.dev = serialstar.SerialStar(port, baudrate, 0.4)

        #  Callback-functions registering.
        self.dev.callback_registring("81", frame_81_received)
        self.dev.callback_registring("83", frame_83_received)
        self.dev.callback_registring("87", frame_87_received)
        self.dev.callback_registring("88", frame_88_received)
        self.dev.callback_registring("89", frame_89_received)
        self.dev.callback_registring("8A", frame_8A_received)
        self.dev.callback_registring("8B", frame_8B_received)
        self.dev.callback_registring("8C", frame_8C_received)
        self.dev.callback_registring("8F", frame_8F_received)
        self.dev.callback_registring("97", frame_97_received)

    def run(self):
        while self.alive:
            # Receive
            frame = self.dev.run()

            # Transmit
            package = None
            global_.mutex.tryLock(timeout=10)
            package = global_.hostData
            global_.mutex.unlock()

            if package is not None:
                package = encrypt_package(package)
                self.dev.send_tx_request('00', TX_ADDR, package, '11')

            package = None
            global_.mutex.tryLock(timeout=10)
            package = global_.specialData
            global_.mutex.unlock()

            if package is not None:
                package = encrypt_package(package)
                self.dev.send_tx_request('00', TX_ADDR, package, '11')


            # Flush dev buffers
            self.t = time.time()
            if ((self.t - self.t_prev) > 5):
                self.t_prev = self.t
                self.dev.ser.flush()
                self.dev.ser.reset_input_buffer()
                self.dev.ser.reset_output_buffer()

        self.off()

    def off(self):
        if self.dev:
            self.dev.ser.close()
            self.dev = None
        pass

def decrypt_package(package):
    try:
        data = package
        package_type = hex_to_int(data[0:8])
        data = data[8:]

        if package_type == 1:
            package = HTRData()
            package.type = 1

            package.acceleration = hex_to_float(data[0:8])
            package.braking = hex_to_float(data[8:16])
            package.velocity = hex_to_float(data[16:24])
            package.mode = hex_to_int(data[24:32])
            package.direction = hex_to_int(data[32:40])
            package.set_base = hex_to_int(data[40:48])

        elif package_type == 2:
            package = RTHData()
            package.type = 2

            package.mode = hex_to_int(data[0:8])
            package.coordinate = hex_to_float(data[8:16])
            package.RSSI = hex_to_float(data[16:24])
            package.voltage = hex_to_float(data[24:32])
            package.current = hex_to_float(data[32:40])
            package.temperature = hex_to_float(data[40:48])
            package.base1 = hex_to_float(data[48:56])
            package.base2 = hex_to_float(data[56:64])
            package.base1_set = hex_to_bool(data[64:66])
            package.base2_set = hex_to_bool(data[66:68])
            package.direction = hex_to_int(data[68:76])

        elif package_type == 3:
            package = HBData()
            package.type = 3

            package.soft_stop = hex_to_bool(data[0:2])
            package.end_points_reset = hex_to_bool(data[2:4])
            package.end_points = hex_to_bool(data[4:6])
            package.end_points_stop = hex_to_bool(data[6:8])
            package.end_points_reverse = hex_to_bool(data[8:10])
            package.sound_stop = hex_to_bool(data[10:12])
            package.swap_direction = hex_to_bool(data[12:14])
            package.accelerometer_stop = hex_to_bool(data[14:16])
            package.HARD_STOP = hex_to_bool(data[16:18])
            package.lock_buttons = hex_to_bool(data[18:20])

        else:
            print('error: no such package')
            return None

        return package

    except ValueError or IndexError:
        print('error')
        return None
    except struct.error as exc:
        print(data)
        print(exc)
        return None


def encrypt_package(package):
    if not package:
        return None

    data = str()
    data += int_to_hex(package.type)

    if package.type == 1:
        data += float_to_hex(package.acceleration)
        data += float_to_hex(package.braking)
        data += float_to_hex(package.velocity)
        data += int_to_hex(package.mode)
        data += int_to_hex(package.direction)
        data += int_to_hex(package.set_base)

    elif package.type == 2:
        data += int_to_hex(package.mode)
        data += float_to_hex(package.coordinate)
        data += float_to_hex(package.RSSI)
        data += float_to_hex(package.voltage)
        data += float_to_hex(package.current)
        data += float_to_hex(package.temperature)
        data += float_to_hex(package.base1)
        data += float_to_hex(package.base2)
        data += bool_to_hex(package.base1_set)
        data += bool_to_hex(package.base2_set)
        data += int_to_hex(package.direction)

    elif package.type == 3:
        data += bool_to_hex(package.soft_stop)
        data += bool_to_hex(package.end_points_reset)
        data += bool_to_hex(package.end_points)
        data += bool_to_hex(package.end_points_stop)
        data += bool_to_hex(package.end_points_reverse)
        data += bool_to_hex(package.sound_stop)
        data += bool_to_hex(package.swap_direction)
        data += bool_to_hex(package.accelerometer_stop)
        data += bool_to_hex(package.HARD_STOP)
        data += bool_to_hex(package.lock_buttons)

    else:
        return None

    return data


def bool_to_hex(c):
    b = struct.pack('>?', c)
    h = binascii.hexlify(b).decode('ascii')
    return h

def int_to_hex(i):
    b = struct.pack('>i', i)
    h = binascii.hexlify(b).decode('ascii')
    return h

def float_to_hex(f):
    b = struct.pack('>f', f)
    h = binascii.hexlify(b).decode('ascii')
    return h

def hex_to_bool(b):
    (x,) = struct.unpack('>?', bytes.fromhex(b))
    return x

def hex_to_int(b):
    (x,) = struct.unpack('>i', bytes.fromhex(b))
    return x

def hex_to_float(b):
    (x,) = struct.unpack('>f', bytes.fromhex(b))
    return x
