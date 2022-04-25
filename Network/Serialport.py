from PyQt5.QtSerialPort import QSerialPort,QSerialPortInfo
from time import sleep
from PyQt5.QtCore import pyqtSignal


class SerialPortLogic():
    serp_signal_write_info = pyqtSignal(str, int)
    serp_signal_write_msg = pyqtSignal(str)

    def __init__(self):
        self.serial=None
        self.link_flag = self.NoLink  # 用于标记是否开启了连接


    def serach_port(self,port):
        port_list=QSerialPortInfo.availablePorts()
        for port in port_list:
            return True
        else:
            msg = '未检测到串口'
            self.serp_signal_write_msg.emit(msg)
            return False

    def serial_port_open(self,port,baud,dataBit,checkBit,stopBit):
        self.serial=QSerialPort()
        self.serial.readyRead.connect(self.read)  #串口接收信号
        ok_port=self.serach_port(port)
        if ok_port:
            self.serial.setPortName(port)
            self.serial.setBaudRate(baud)
            self.serial.setDataBits(dataBit)
            self.serial.setParity(checkBit)
            self.serial.setStopBits(stopBit)
        else:
            msg = '未检测到串口'
            self.serp_signal_write_msg.emit(msg)
        try:
           if not self.serial.open(QSerialPort.ReadWrite):
               msg='打开串口失败'
               self.serp_signal_write_msg.emit(msg)
           else:
               msg='串口：'+port
               self.serp_signal_write_msg.emit(msg)

        except Exception as e:
            pass

    def read(self):

        revData=self.serial.readAll()
        if revData:
            info = bytes(revData) #将Qbytes转化为bytes
            msg='接收：'
            self.serp_signal_write_msg.emit(msg)
            try:
                info_decoded = info.decode("utf-8")
                self.serp_signal_write_info.emit(info_decoded, self.InfoRec)
            except Exception as ret:
                if info.hex():  # 将16进制bytes b'\xaa'转换成utf-8 str 'aa'
                    info_decoded = info.hex()
                    self.serp_signal_write_info.emit(info_decoded, self.InfoRec)
                else:
                    msg = "数据格式错误" + ret.__str__()
                    self.serp_signal_write_msg.emit(msg)
        else:
            sleep(0.02)
            if not self.serial.waitForReadyRead():
                self.serial.close()
                msg='串口已断开..'
                self.serp_signal_write_msg.emit(msg)


    def write(self,info):
        self.serial.write(info.encode('utf-8'))
        msg = '已发送'
        self.serp_signal_write_msg.emit(msg)
        self.serp_signal_write_info.emit(info,self.InfoSend)

    def serial_port_close(self):
        self.serial.close()
        msg='串口已断开'
        self.serp_signal_write_msg.emit(msg)



    NoLink = -1
    InfoSend = 0
    InfoRec = 1