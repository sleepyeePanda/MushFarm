class UartProtocol(asyncio.Protocol):
    def __init__(self, uartCom):
        super().__init__()
        self.uartCom = uartCom
        self.rcvParser = RcvParser()

    def connection_made(self, transport):
        self.transport = transport
        print('port opened', transport)
        transport.serial.rts = False
        self.uartCom.uart = transport

    def data_received(self, data):
        message = data.decode()
        self.rcvParser.parsing(message)

    def connection_lost(self, exc):
        print('port closed')
        self.transport.loop.stop()


class RcvParser(QtCore.QObject):
    updateStateSignal = QtCore.pyqtSignal()
    updateActuatorSignal = QtCore.pyqtSignal()
    updateGraphSignal = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_protocol()
        self.updateStateSignal.connect(manager.update_state)
        self.updateActuatorSignal.connect(manager.update_actuator)
        self.updateGraphSignal.connect(manager.update_graph)
        ui.temp_check.clicked.connect(manager.update_graph)
        ui.humid_check.clicked.connect(manager.update_graph)
        ui.co2_check.clicked.connect(manager.update_graph)

    def parsing(self, pkt):
        self.info = pkt.strip(r'\x02\x03\n\r')
        print('data parsed', self.info)
        cmd = self.info[0]
        try:
            func = self.protocol.get(cmd)
            return func(self.info)
        except Exception as e:
            print(str(e))

    def rcv_state(self, info):
        values.time = datetime.datetime.now().strftime('%H : %M : %S')
        try:
            temp = float(info[3:8])
        except Exception as e:
            print(str(e))
            temp = values.temp[-1]
        try:
            humid = float(info[9:11])
        except Exception as e:
            print(str(e))
            humid = values.humid[-1]
        try:
            co2 = float(info[12:16])
        except Exception as e:
            print(str(e))
            co2 = values.co2[-1]
        self.updateStateSignal.emit()
        values.temp.pop(0)
        values.humid.pop(0)
        values.co2.pop(0)

    def rcv_heater(self, info):
        try:
            values.status['heater'] = True if info[4] == 'O' else False
        except Exception as e:
            print(str(e))
        self.updateActuatorSignal.emit()

    def rcv_humid(self, info):
        try:
            values.status['humidifier'] = True if info[4] == 'O' else False
        except Exception as e:
            print(str(e))
        self.updateActuatorSignal.emit()

    def rcv_fan(self, info):
        try:
            values.status['fan'] = True if info[4] == 'O' else False
        except Exception as e:
            print(str(e))
        self.updateActuatorSignal.emit()

    def rcv_dryer(self, info):
        try:
            values.status['dryer'] = True if info[4] == 'O' else False
        except Exception as e:
            print(str(e))
        self.updateActuatorSignal.emit()

    def rcv_led(self, info):
        try:
            values.status['led'] = True if info[4] == 'O' else False
        except Exception as e:
            print(str(e))
        self.updateActuatorSignal.emit()

    def init_protocol(self):
        self.protocol = {'S1': self.rcv_state,
                         'MF': self.rcv_heater,
                         'MH': self.rcv_humid,
                          #'MF': self.rcv_fan,
                         'ML': self.rcv_led}