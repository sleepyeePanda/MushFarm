import asyncio
import datetime
import glob
import json
from functools import partial
import serial
from threading import Thread
import time

from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg
import serial_asyncio

from monitor_ui import Ui_MainWindow
import values


class UartCom:
    def __init__(self):
        self.get_com()
        ui.connect.clicked.connect(self.connect_serial)
        ui.disconnect.clicked.connect(self.disconnect_serial)
        ui.heater.clicked.connect(partial(self.control_heater_power, init=False))
        ui.humidifier.clicked.connect(partial(self.control_humid_power, init=False))
        ui.fan.clicked.connect(partial(self.control_fan_power, init=False))
        # ui.dryer.clicked.connect(self.control_dryer_power)
        ui.led.clicked.connect(partial(self.control_led_power, init=False))
        ui.start.clicked.connect(lambda: self.manual_start() if ui.manu_apply.isChecked() else self.auto_start())
        ui.start.toggled.connect(lambda x: ui.start.setText('\n\n실행 중') if x else ui.start.setText('\n\n시작'))
        ui.manu_apply.clicked.connect(lambda: ui.auto_apply.setChecked(False))
        ui.auto_apply.clicked.connect(lambda: ui.manu_apply.setChecked(False))
        self.manual_timer = None
        self.auto_timer = None
        self.uart = None
        self.isLinux = False
        self.writer = None
        self.t = None
        self.connect_serial()

    def get_com(self, waiting=0):
        time.sleep(waiting)
        connect_port = []
        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            self.isLinux = True
        else:
            self.isLinux = False
        if self.isLinux:
            ports = self.serial_ports()
            for port in ports:
                if port.find('USB') > -1:
                    connect_port.append(port)
                    self.connect_serial()
        else:
            ports = self.serial_ports()
            for port in ports:
                if port.find('COM') > -1:
                    connect_port.append(port)
        print(connect_port)
        if not connect_port:
            manager.alertSignal.emit('통신 연결을 확인한 후 프로그램을 재실행 해주십시오')
        else:
            for comport in connect_port:
                ui.coms.addItem(comport)

    def serial_ports(self):
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal '/dev/tty'
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')
        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

    def run(self, loop, coro):
        try:
            loop.run_forever()
        except serial.serialutil.SerialException as se:
            print(str(se))
            print('serial exception occured')
        except Exception as e:
            print(str(e))
        finally:
            loop.stop()
            loop.close()
        print('Closed Uart Thread!')

    def connect_serial(self):
        com_no = str(ui.coms.currentText())
        print(com_no)
        if com_no:
            self.loop = asyncio.get_event_loop()
            if self.isLinux:
                self.writer = serial_asyncio.create_serial_connection(self.loop, lambda: UartProtocol(self), com_no,
                                                                      baudrate=115200)
                print(str(com_no)+' connected')
            else:
                self.writer = serial_asyncio.create_serial_connection(self.loop, lambda: UartProtocol(self), com_no,
                                                                      baudrate=115200)
                print(str(com_no)+' connected')

            self.t = Thread(target=self.run, args=(self.loop, self.writer))
            self.t.setDaemon(True)
            self.t.start()

            ui.connect.setText('완료')
            ui.connect.setChecked(True)
            ui.connect.setEnabled(False)
            ui.coms.setEnabled(False)
        else:
            ui.connect.setText('연결')
            ui.connect.setChecked(False)
            ui.coms.setEnabled(True)

    def disconnect_serial(self):
        if self.uart is not None:
            self.uart.close()
            self.uart = None
        ui.coms.clear()
        self.get_com(0.3)
        ui.connect.setChecked(False)
        ui.connect.setText('연결')
        ui.connect.setEnabled(True)
        ui.coms.setEnabled(True)
        ui.disconnect.setChecked(False)

    def send_init(self):
        if self.uart is not None:
            self.control_heater_power(init=True)
            time.sleep(0.15)
            self.control_humid_power(init=True)
            time.sleep(0.15)
            self.control_fan_power(init=True)
            time.sleep(0.15)
            self.control_led_power(init=True)
            time.sleep(0.15)

    def send_msg(self, msg):
        if self.uart is not None:
            try:
                self.uart.write(msg.encode())
                print(msg)
                return True
            except Exception as e:
                print(str(e))
                manager.alertSignal.emit('통신 연결 상태를 확인해 주십시오.')
                return False
        else:
            manager.alertSignal.emit('통신 연결 상태를 확인해 주십시오.')
            print('Not Connected')
            return False

    def send_state(self):
        self.send_msg(r'\x02S1TEMP?\x03\x0A\x0D')

    def control_heater_power(self, init=False):
        msgs = {True: r'\x02MF1FX\x03\x0A\x0D', False: r'\x02MF1FO\x03\x0A\x0D'}
        self.send_msg(r'\x02MF1ST\x03\x0A\x0D' if init else msgs[values.status['heater']])

    def control_humid_power(self, init=False, order=None):
        msgs = {True: r'\x02MH1FX\x03\x0A\x0D', False: r'\x02MH1FO\x03\x0A\x0D'}
        if order is not None:
            msg = msgs[order]
            self.humid_act_timer = QtCore.QTimer()
            self.humid_act_timer.setSingleShot(True)
            self.humid_act_timer.timeout.connect(lambda: self.control_humid_power(order=True))
            # hours*60*60*1000msec
            # minutes*60*1000msec
            self.humid_act_timer.start(values.manu_settings['humidifier']['act'][0]*3600000
                                       + values.manu_settings['humidifier']['act'][1]*60000)
        else:
            msg = msgs[values.status['humidifier']]
        self.send_msg(r'\x02MH1ST\x03\x0A\x0D' if init else msg)

    def control_fan_power(self, init=False):
        msgs = {True: r'\x02MF1FX\x03\x0A\x0D', False: r'\x02MF1FO\x03\x0A\x0D'}
        self.send_msg(r'\x02MF1ST\x03\x0A\x0D' if init else msgs[values.status['fan']])

    def control_led_power(self, init=False):
        msgs = {True: r'\x02ML1FX\x03\x0A\x0D', False: r'\x02ML1FO\x03\x0A\x0D'}
        self.send_msg(r'\x02ML1ST\x03\x0A\x0D' if init else msgs[values.status['led']])

    def auto_start(self):
        msg = r'\x02ART'+str(values.auto_settings['temp'][0])+'H'+str(values.auto_settings['humid'][0])+ \
              'C'+str(values.auto_settings['co2'][0])+r'I000\x03\x0A\x0D'
        if self.send_msg(msg):
            ui.start_back.setChecked(True)
            self.auto_timer = QtCore.QTimer()
            self.auto_timer.setSingleShot(True)
            self.auto_timer.timeout.connect(self.auto_stop)
            self.auto_timer.start(values.auto_settings['actTime'][0]*8640000 +
                                  values.auto_settings['actTime'][1]*360000)
        else:
            ui.start_back.setChecked(False)

    def auto_stop(self):
        self.send_msg(r'\x02ARSTOP\x03\x0A\x0D')

    def manual_start(self):
        msg = r'\x02ART'+str(values.manu_settings['temp'][0])+'H'+str(values.manu_settings['humid'][0])+ \
              'C'+str(values.manu_settings['co2'][0])+r'I000\x03\x0A\x0D'
        if self.send_msg(msg):
            ui.start_back.setChecked(True)
            self.manual_timer = QtCore.QTimer()
            self.manual_timer.setSingleShot(True)
            self.manual_timer.timeout.connect(self.manual_stop)
            self.humid_freq_timer = QtCore.QTimer()
            self.humid_freq_timer.setSingleShot(True)
            self.humid_freq_timer.timeout.connect(lambda: self.control_humid_power(init=False, order=False))
            self.progress_timer = QtCore.QTimer()
            self.progress_timer.setSingleShot(True)
            self.progress_timer.timeout.connect(self.update_progress)
            # days*60*60*24*1000msec
            # hours*60*60*1000msec
            # minutes*60*1000msec
            self.grow_time = values.manu_settings['growTime'][0]*86400000 + values.manu_settings['growTime'][1]*3600000
            self.grow_time = 6000
            self.manual_timer.start(self.grow_time)
            self.humid_freq_timer.start(values.manu_settings['humidifier']['freq'][0]*3600000 +
                                        values.manu_settings['humidifier']['freq'][1]*60000)
            self.progress_timer.start(1000)
        else:
            ui.start_back.setChecked(False)

    def update_progress(self):
        ui.progressBar.setValue(((self.grow_time - self.manual_timer.remainingTime()) / self.grow_time)*100)

    def manual_stop(self):
        self.send_msg(r'\x02MRSTOP\x03\x0A\x0D')


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


class TimeUpdater(QtCore.QThread):
    def __init__(self):
        super().__init__()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.change_time)
        self.timer.start(1000)
        self.start()

    def change_time(self):
        ui.cur_time.setText(QtCore.QTime.currentTime().toString('hh : mm : ss'))


class ValueUpdater(QtCore.QThread):
    def __init__(self):
        super().__init__()
        uartCom.send_init()
        sens_timer = QtCore.QTimer()
        sens_timer.timeout.connect(uartCom.send_state)
        sens_timer.start(3000)
        self.start()


class Manager(QtCore.QThread):
    alertSignal = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.alertSignal.connect(self.alert)
        buttons = [ui.graph_l, ui.settings_r, ui.main_r, ui.settings_l, ui.main_l, ui.graph_r]
        for i, button in enumerate(buttons):
            button.clicked.connect(partial(ui.stackedWidget.setCurrentIndex, i//2))

        ui.manual_mode.clicked.connect(lambda: ui.stackedWidget_2.setCurrentIndex(0))
        ui.manual_mode.clicked.connect(lambda: self.update_settings('manual'))
        ui.auto_mode.clicked.connect(lambda: ui.stackedWidget_2.setCurrentIndex(1))
        ui.auto_mode.clicked.connect(lambda: self.update_settings('auto'))
        ui.manu_apply.clicked.connect(lambda: self.change_settings('manual'))
        ui.auto_apply.clicked.connect(lambda: self.change_settings('auto'))
        ui.temp_check.clicked.connect(self.update_graph)
        ui.humid_check.clicked.connect(self.update_graph)
        ui.co2_check.clicked.connect(self.update_graph)
        ui.fix_check.clicked.connect(lambda: self.fix_graph(fix=True))
        ui.unfix_check.clicked.connect(lambda: self.fix_graph(fix=False))
        ui.power.clicked.connect(sys.exit)

        # initializing

        self.update_settings('auto')
        self.update_settings('manual')
        self.update_graph()

    def update_settings(self, mode):
        if mode == 'manual':
            ui.settings_temp.setText(str(values.manu_settings['temp'][0]))
            ui.temp_dial.setMaximum(int(values.manu_settings['temp'][0]*2))
            ui.settings_humid.setText(str(values.manu_settings['humid'][0]))
            ui.humid_dial.setMaximum(int(values.manu_settings['humid'][0]))
            ui.settings_co2.setText(str(values.manu_settings['co2'][0]))
            ui.co2_dial.setMaximum(int(values.manu_settings['co2'][0]*2))
            ui.manu_temp.setValue(values.manu_settings['temp'][0])
            ui.manu_temp_range.setValue(values.manu_settings['temp'][1])
            ui.manu_humid.setValue(values.manu_settings['humid'][0])
            ui.manu_humid_range.setValue(values.manu_settings['humid'][1])
            ui.manu_co2.setValue(values.manu_settings['co2'][0])
            ui.manu_co2_range.setValue(values.manu_settings['co2'][1])
            ui.manu_days.setValue(values.manu_settings['growTime'][0])
            ui.manu_hours.setValue(values.manu_settings['growTime'][1])
            ui.humid_freq_h.setValue(values.manu_settings['humidifier']['freq'][0])
            ui.humid_freq_m.setValue(values.manu_settings['humidifier']['freq'][1])
            ui.humid_act_h.setValue(values.manu_settings['humidifier']['act'][0])
            ui.humid_act_m.setValue(values.manu_settings['humidifier']['act'][1])
        else:
            ui.settings_temp.setText(str(values.auto_settings['temp'][0]))
            ui.settings_humid.setText(str(values.auto_settings['humid'][0]))
            ui.settings_co2.setText(str(values.auto_settings['co2'][0]))
            ui.auto_temp.setValue(values.auto_settings['temp'][0])
            ui.auto_temp_range.setValue(values.auto_settings['temp'][1])
            ui.auto_humid.setValue(values.auto_settings['humid'][0])
            ui.auto_humid_range.setValue(values.auto_settings['humid'][1])
            ui.auto_co2.setValue(values.auto_settings['co2'][0])
            ui.auto_co2_range.setValue(values.auto_settings['co2'][1])
            ui.auto_days.setValue(values.auto_settings['actTime'][0])
            ui.auto_hours.setValue(values.auto_settings['actTime'][1])

    def alert(self, message):
        msgbox = QtWidgets.QMessageBox()
        msgbox.setIcon(QtWidgets.QMessageBox.Information)
        msgbox.setText(message)
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        subapp = msgbox.exec_()

    def save_data(self):
        pass

    def button_test(self):
        ui.heater.setEnabled(True)

    def update_state(self):
        ui.cur_temp_1.setText(str(float(values.temp)))
        ui.temp_dial.setValue(int(values.temp))
        ui.cur_humid_1.setText(str(int(values.humid)))
        ui.humid_dial.setValue(int(values.humid))
        ui.cur_co2_1.setText(str(int(values.co2)))
        ui.co2_dial.setValue(int(values.co2))
        ui.sens_time.setText(values.time)

    def update_actuator(self):
        ui.heater_back.setChecked(values.status['heater'])
        ui.humidifier_back.setChecked(values.status['humidifier'])
        ui.fan_back.setChecked(values.status['fan'])
        # ui.dryer_back.setChecked(values.status['dryer'])
        ui.led_back.setChecked(values.status['led'])

    def update_graph(self):
        ui.graphicsView.clear()
        ui.cur_temp_2.setText(str(float(values.temp[-1])))
        ui.cur_humid_2.setText(str(int(values.humid[-1])))
        ui.cur_co2_2.setText(str(int(values.co2[-1])))

        ui.graphicsView.clear()

        global main_view, humid_view, co2_view
        main_view.clear()
        if ui.temp_check.isChecked():
            main_view.addItem(pg.PlotCurveItem(values.temp, pen=pg.mkPen(color='#FF8200', width=3)))
        humid_view.clear()
        if ui.humid_check.isChecked():
            humid_view.addItem(pg.PlotCurveItem(values.humid, pen=pg.mkPen(color='#1EDC00', width=3)))
        co2_view.clear()
        if ui.co2_check.isChecked():
            co2_view.clear()
            co2_view.addItem(pg.PlotCurveItem(values.co2, pen=pg.mkPen(color='#B400FA', width=3)))

    def fix_graph(self, fix=True):
        # fix is True or False
        if fix:
            main_view.setLimits(yMin=0, yMax=100)
            humid_view.setLimits(yMin=0, yMax=100)
            co2_view.setLimits(yMin=0, yMax=2000)
        else:
            main_view.setLimits(yMin=-100, yMax=200)
            humid_view.setLimits(yMin=-100, yMax=200)
            co2_view.setLimits(yMin=-5000, yMax=5000)
        main_view.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=fix)
        humid_view.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=fix)
        co2_view.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=fix)

    def update_view(self, humid_v, co2_v, v):
        humid_v.setGeometry(v.sceneBoundingRect())
        co2_v.setGeometry(v.sceneBoundingRect())

    def change_settings(self, mode):
        if mode == 'manual':
            values.manu_settings['temp'] = [ui.manu_temp.value(), ui.manu_temp_range.value()]
            values.manu_settings['humid'] = [ui.manu_humid.value(), ui.manu_humid_range.value()]
            values.manu_settings['co2'] = [ui.manu_co2.value(), ui.manu_co2_range.value()]
            values.manu_settings['growTime'] = [ui.manu_days.value(), ui.manu_hours.value()]
            values.manu_settings['humidifier']['freq'] = [ui.humid_freq_h.value(), ui.humid_freq_m.value()]
            values.manu_settings['humidifier']['act'] = [ui.humid_act_h.value(), ui.humid_act_m.value()]
        else:
            values.auto_settings['temp'] = [ui.auto_temp.value(), ui.auto_temp_range.value()]
            values.auto_settings['humid'] = [ui.auto_humid.value(), ui.auto_humid_range.value()]
            values.auto_settings['co2'] = [ui.auto_co2.value(), ui.auto_co2_range.value()]
            values.auto_settings['actTime'] = [ui.auto_days.value(), ui.auto_hours.value()]


def load_settings():
    with open('config.json', 'r') as file:
        data = json.load(file)
        values.manu_settings = data['manu_settings']
        values.auto_settings = data['auto_settings']


def save_settings():
    with open('config.json', 'w') as file:
        json.dump({'manu_settings': values.manu_settings, 'auto_settings': values.auto_settings}, file, indent=4)


def updateViews(main_view, humid_view, co2_view):
    humid_view.setGeometry(main_view.sceneBoundingRect())
    co2_view.setGeometry(main_view.sceneBoundingRect())


if __name__ == '__main__':
    import sys
    pg.setConfigOption('foreground', 'k')
    pg.setConfigOption('background', 'w')
    pg.setConfigOptions(antialias=True)
    INSERT_DATA = 'INSERT INTO data(time, temperature, humidity, co2) VALUES(?, ?, ?, ?)'
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(mainWindow)

    font11 = QtGui.QFont('나눔스퀘어', 11)

    humid_axis = pg.AxisItem('left')
    humid_axis.tickFont = font11
    humid_view = pg.ViewBox()

    layout = pg.GraphicsLayout()
    ui.graphicsView.setCentralWidget(layout)

    layout.addItem(humid_axis, row=2, col=1, rowspan=1, colspan=1)

    plotItem = pg.PlotItem()
    plotItem.getAxis('left').tickFont = font11
    plotItem.getAxis('left').setWidth(60)
    plotItem.getAxis('bottom').tickFont = QtGui.QFont('나눔스퀘어', 11)
    plotItem.showGrid(True, True, 0.5)
    main_view = plotItem.vb
    layout.addItem(plotItem, row=2, col=2, rowspan=1, colspan=1)

    layout.scene().addItem(humid_view)
    humid_axis.linkToView(humid_view)
    humid_view.setXLink(main_view)
    humid_axis.setWidth(60)

    co2_view = pg.ViewBox()
    co2_axis = pg.AxisItem('right')
    co2_axis.tickFont = font11
    plotItem.layout.addItem(co2_axis, 2, 3)
    plotItem.scene().addItem(co2_view)
    co2_axis.linkToView(co2_view)
    co2_view.setXLink(plotItem)
    co2_axis.setWidth(60)

    main_view.sigResized.connect(lambda: updateViews(main_view, humid_view, co2_view))

    humid_view.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
    co2_view.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)

    load_settings()
    manager = Manager()
    uartCom = UartCom()
    timeUpdater = TimeUpdater()
    valueUpdater = ValueUpdater()
    # MainWindow.showFullScreen()
    mainWindow.show()
    app.exec_()
    if uartCom.t and uartCom.t.isAlive():
        uartCom.uart.loop.call_soon_threadsafe(uartCom.uart.loop.stop)
    save_settings()
    sys.exit()
