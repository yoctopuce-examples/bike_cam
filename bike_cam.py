#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import posixpath
import socket
import urllib
from typing import Any, Union

from zeroconf import Zeroconf, ServiceBrowser

import virb
import datetime
import threading
from yoctopuce.yocto_api import *
from yoctopuce.yocto_buzzer import YBuzzer
from yoctopuce.yocto_buzzer import *
from yoctopuce.yocto_accelerometer import *
from http.server import BaseHTTPRequestHandler, HTTPServer, SimpleHTTPRequestHandler
from urllib import parse


class Action(object):
    def __init__(self, app_ref):
        self._app = app_ref

    def trigger(self):
        pass

    def get_status(self):
        return ""


class BuzzerAction(Action):

    def __init__(self, app_ref):
        super(BuzzerAction, self).__init__(app_ref)
        self._buzzer = None

    def trigger(self):
        if self._buzzer is not None:
            self._buzzer.playNotes("'E32 C8")

    def configure(self, hwid):
        self._buzzer = YBuzzer.FindBuzzer(hwid)
        self._buzzer.playNotes("C32! -'G C")

    def stop(self):
        self._buzzer = None

    def get_status(self):
        if self._buzzer is not None:
            return "ok"
        else:
            return "no buzzer detected"


class VirbAction(Action):

    def __init__(self, app_ref, ip, durration):
        super(VirbAction, self).__init__(app_ref)
        self._virb = None
        self.record_duration = durration
        self._expiration = datetime.datetime.now()

    def get_duration(self):
        return self.record_duration

    def configure(self, ip):
        self._virb = virb.Virb(ip)
        self._virb.test_connection()
        pass

    def trigger(self):
        if self._virb is None:
            return
        self._expiration = datetime.datetime.now() + datetime.timedelta(seconds=self.record_duration)
        self._virb.start_recording()
        timer = threading.Timer(self.record_duration, self.check_stop)
        timer.start()

    def check_stop(self):
        if self._virb is None:
            return
        if self._expiration <= datetime.datetime.now():
            self._virb.stop_recording()

    def get_status(self):
        if self._virb is not None:
            return "ok"
        else:
            return "no camera detected"


class Detector(object):
    def __init__(self, app_ref, actions):
        """

        :type actions: Action[]
        :type app_ref: App
        """
        self._is_trigered = False
        self._limit = 500
        self._app = app_ref
        self._actions = actions

    def configure(self, hwid):
        pass

    def stop(self):
        pass

    def set_on(self):
        if not self._is_trigered:
            self.trigger()
        self._is_trigered = True

    def trigger(self):
        print("trigger recording")
        for action in self._actions:
            action.trigger()

    def set_off(self):
        self._is_trigered = False


class Yocto3DDetector(Detector):
    def __init__(self, app_ref, actions):
        """

        :type actions: Action[]
        :type app_ref: App
        """
        super(Yocto3DDetector, self).__init__(app_ref, actions)
        self._vibration_duration = datetime.timedelta(seconds=4)
        self._reftime = datetime.datetime.now()
        self._last_time = YAPI.GetTickCount()
        self._lastvalue = 0
        self._limit = 500
        self._accel = None

    def configure(self, hwid):
        self._accel = YAccelerometer.FindAccelerometer(hwid)
        self._accel.set_gravityCancellation(YAccelerometer.GRAVITYCANCELLATION_ON)
        self._accel.registerValueCallback(self.valueCb)

    def stop(self):
        self._accel = None

    def valueCb(self, accel, str_val):
        """

        :param accel: YAccelerometer
        :type str_val: str
        """

        value = float(str_val)
        now = datetime.datetime.now()
        t = now - self._reftime
        print("Accel: %f (was %f ) %f" % (value, self._lastvalue, t.microseconds))
        if (now - self._last_time) > self._vibration_duration:
            self.trigger()
        self._lastvalue = value
        self._last_time = now

    def get_status(self):
        if self._accel is not None:
            return "ok"
        else:
            return "no Yocto-3D detected"


class ReqHandler(SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path.startswith("/status.json"):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            args = dict(parse.parse_qsl(parse.urlsplit(self.path).query))
            if 'duration' in args:
                self.server.update_duration(args['duration'])
            status = self.server.getStatus()
            self.wfile.write(json.dumps(status).encode())
        else:
            SimpleHTTPRequestHandler.do_GET(self)

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """

        # abandon query parameters
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        # Don't forget explicit trailing slash when normalizing. Issue17324
        trailing_slash = path.rstrip().endswith('/')
        try:
            path = urllib.parse.unquote(path, errors='surrogatepass')
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        path = posixpath.normpath(path)
        words = path.split('/')
        words = filter(None, words)
        path = os.path.dirname(__file__) + "/http"
        for word in words:
            if os.path.dirname(word) or word in (os.curdir, os.pardir):
                # Ignore components that are not a simple file/directory name
                continue
            path = os.path.join(path, word)
        if trailing_slash:
            path += '/'
        return path


class BikeCam_srv(HTTPServer):

    def __init__(self, url, interface):
        self._http_port = 8000
        server_address = ('', self._http_port)
        super().__init__(server_address, ReqHandler)
        self._url = url
        self._duration = 10
        errmsg = YRefParam()
        if YAPI.RegisterHub(self._url, errmsg) != YAPI.SUCCESS:
            self.fatal_error("RegisterHub error" + errmsg.value)
        self.buzzer_action = BuzzerAction(self)
        self.cam_action = VirbAction(self, interface, self._duration)
        actions = [self.cam_action, self.buzzer_action]
        self.detector = Yocto3DDetector(self, actions)
        YAPI.RegisterDeviceArrivalCallback(self.deviceArrival)
        YAPI.RegisterDeviceRemovalCallback(self.deviceRemoval)
        self._zeroconf = Zeroconf()
        browser = ServiceBrowser(self._zeroconf, "_garmin-virb._tcp.local.", self)

    def remove_service(self, zeroconf, type, name):
        print("Service %s removed" % (name,))

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        ip = socket.inet_ntoa(info.address)
        print("Service %s detected with ip  %s" % (name, ip))
        self.cam_action.configure(ip)

    def deviceArrival(self, module):
        """

        :type module: YModule
        """
        serial = module.get_serialNumber()
        product_name = module.get_productName()
        print(product_name + ' arrival : ' + serial)
        if product_name == "Yocto-Buzzer":
            self.buzzer_action.configure(serial + ".buzzer")
        elif product_name == "Yocto-3D" or product_name == "Yocto-3D-V2":
            self.detector.configure(serial + ".accelerometer")

    def deviceRemoval(self, module):
        """

        :type module: YModule
        """
        serial = module.get_serialNumber()
        product_name = module.get_productName()
        print(product_name + ' removal : ' + serial)
        if product_name == "Yocto-Buzzer":
            self.buzzer_action.stop()
        elif product_name == "Yocto-3D" or product_name == "Yocto-3D-V2":
            self.detector.stop()

    def start(self):
        errmsg = YRefParam()
        while True:
            if YAPI.HandleEvents(errmsg) != YAPI.SUCCESS:
                self.fatal_error(errmsg.value)
            if YAPI.UpdateDeviceList(errmsg) != YAPI.SUCCESS:
                self.fatal_error(errmsg.value)
            self.handle_request()

    def fatal_error(self, msg):
        YAPI.FreeAPI()
        self._zeroconf.close()
        sys.exit("Fatal Error:" + msg)

    def doPouet(self):
        self.buzzer_action.trigger()

    def getStatus(self):
        return {"buzzer": self.buzzer_action.get_status(),
                "y3d": self.detector.get_status(),
                'virb': self.cam_action.get_status(),
                'duration': self.cam_action.get_duration()}

    def update_duration(self, duration):
        self.cam_action.record_duration = int(duration)


# Execute the application
if __name__ == "__main__":
    # app = BikeCam_srv("usb", "192.168.88.1")
    app = BikeCam_srv("usb", "172.17.17.97")
    app.start()
