from threading import Thread


import requests
import json


class Virb(object):
    def __init__(self, ip):
        self._ip = ip

    def _send_command(self, data):
        json_data = json.dumps(data)
        r = requests.post("http://%s/virb" % self._ip, data=json_data)
        if r.status_code != 200:
            raise Exception("Virb returned HTTP %d %s for request %s" % (r.status_code, r.reason, data['command']))
        res = json.loads(r.text)
        if res['result'] != 1:
            raise Exception("Virb returned error code %d for request %s" % (res['result'], data['command']))
        return res

    def test_connection(self):
        status = self.get_status()
        # print(status)
        charge_state = ''
        if status['batteryChargingState'] > 0:
            charge_state = ' (charging)'
        print("Virb battery : %d%%%s" % (status['batteryLevel'], charge_state))
        res = self.get_commandList()
        print("Supported command:")
        for command in res['commandList']:
            print(" - %s(%d)" % (command['command'], command['version']))

        print("Virb status is %s" % (status['state']))
        if status['state'] != 'idle':
            print("stop recording...")
            self.stop_recording()
            print("Virb status is %s" % (status['state']))

    def start_recording(self):
        self._send_command({"command": "startRecording"})

    def stop_recording(self):
        self._send_command({"command": "stopRecording"})

    def get_status(self):
        res = self._send_command({"command": "status"})
        return res

    def get_features(self):
        res = self._send_command({"command": "features"})
        return res

    def get_commandList(self):
        res = self._send_command({"command": "commandList"})
        return res

    def get_mediaList(self):
        res = self._send_command({"command": "mediaList"})
        return res

