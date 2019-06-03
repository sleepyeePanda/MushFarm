import asyncio
from PyQt5 import QtCore

class UartProtocol(asyncio.Protocol):
    def __init__(self):
        super().__init__()
        self.rcvParser = RcvParser()

    def connection_made(self, transport):
        self.transport = transport
        print('port opened', transport)
        transport.serial.rts = False
        self.rcvParser.transport = transport

    def data_received(self, data):
        message = data.decode()
        self.rcvParser.parsing(message)

    def connection_lost(self, exc):
        print('port closed')
        self.transport.loop.stop()


class RcvParser(QtCore.QObject):

    def __init__(self):
        super().__init__()
        self.init_protocol()
        self.transport = None

    def parsing(self, pkt):
        self.info = pkt.strip(r'\x02\x03\n\r')
        print('data parsed', self.info)
        cmd = self.info[0]
        try:
            func = self.protocol.get(cmd)
            return func(self.info)
        except Exception as e:
            print(str(e))

    def send_msg(self, msg):
        if self.transport is not None:
            try:
                self.transport.write(msg.encode())
                print(msg)
                return True
            except Exception as e:
                print(str(e), 'occured in remote')
                return False
        else:
            print('Remote Not Connected')

    def send_state(self):
        self.send_msg('\x02S1T+50.5H25C1000I000\x03\x0A\x0D')

    def send_heater(self, info):
        if info[3] == 'S':
            self.send_msg('\x02MF1FO\x03\x0A\x0D')
        else:
            self.send_msg(info)

    def send_humid(self, info):
        if info[3] == 'S':
            self.send_msg('\x02MH1FO\x03\x0A\x0D')
        else:
            self.send_msg(info)

    def send_fan(self, info):
        if info[3] == 'S':
            self.send_msg('\x02MF1FO\x03\x0A\x0D')
        else:
            self.send_msg(info)

    def send_dryer(self, info):
        if info[3] == 'S':
            self.send_msg('\x02MF1FO\x03\x0A\x0D')
        else:
            self.send_msg(info)

    def send_led(self, info):
        if info[3] == 'S':
            self.send_msg('\x02ML1FO\x03\x0A\x0D')
        else:
            self.send_msg(info)

    def init_protocol(self):
        self.protocol = {'S1': self.send_state,
                         'MF': self.send_heater,
                         'MH': self.send_humid,
                          #'MF': self.send_fan,
                         'ML': self.send_led}
