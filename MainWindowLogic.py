from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QWidget
from PyQt5 import QtWidgets,QtCore, QtGui
import datetime
import base64
import logging
from logging import config
from Network import get_host_ip
from UI import MainWindowUI
from UI.MyWidgets import PortInputDialog
from log import Log


class WidgetLogic(QWidget):
    link_signal = pyqtSignal(tuple)  # 连接类型, 目标IP, 本机/目标端口
    seri_link_signal=pyqtSignal(tuple) #串口类型
    disconnect_signal = pyqtSignal()
    send_signal = pyqtSignal(str)
    counter_signal = pyqtSignal(int, int)
    ParityDic = {'NONE': 0, 'ODD': 3, 'EVEN': 2, 'MARK': 5, 'SPACE': 4}
    StopbitDic = {'1 bit': 1, '1.5 bit': 3, '2 bit': 2}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.log=Log(__name__).getlog()
        self.__ui = MainWindowUI.Ui_Form()
        self.__ui.setupUi(self)
        self.__ui.retranslateUi(self)
        self.log.info('started')
        self.setWindowFlags(Qt.WindowStaysOnTopHint)  # 保持窗口最前
        self.__ui.MyHostAddrLineEdit.setText(get_host_ip())  # 显示本机IP地址

        self.protocol_type = "TCP Server"
        self.link_flag = self.NoLink
        self.receive_show_flag = True  # 是否显示接收到的消息
        self.send_HEX_flag=False       #是否以十六进制发送
        self.receive_HEX_flag=False    #是否以十六进制接收
        self.SendCounter = 0
        self.ReceiveCounter = 0
        self.dir = None

        self.counter_signal.connect(self.counter_signal_handler)
        self.__ui.ProtocolTypeComboBox.activated[str].connect(
            self.protocol_type_combobox_handler
        )
        self.__ui.ConnectButton.toggled.connect(self.connect_button_toggled_handler)
        self.__ui.SendButton.clicked.connect(self.send_link_handler)
        self.__ui.OpenFilePushButton.clicked.connect(self.open_file_handler)
        self.__ui.RSaveDataButton.clicked.connect(self.r_save_data_button_handler)
        self.__ui.CounterResetLabel.clicked.connect(self.counter_reset_button_handler)
        self.__ui.ReceivePauseCheckBox.toggled.connect(
            self.receive_pause_checkbox_toggled_handler
        )
        self.__ui.HEXReceiveCheckBox.toggled.connect(self.receive_HEX_checkbox_toggled_handler)
        self.__ui.SendHEXCheckBox.toggled.connect(self.send_HEX_checkbox_toggled_handler)
        self.__ui.openButton.toggled.connect(self.serial_connect_button_toggle_handler)


    def connect_button_toggled_handler(self, state):
        if state:
            # 连接按钮连接
            self.click_link_handler()
        else:
            # 连接按钮断开连接
            self.click_disconnect()
            self.editable(True)

    def serial_connect_button_toggle_handler(self,state):
        if state:
            self.serial_click_link_handler()
        else:
            self.click_disconnect()
            self.serial_editable(True)


    def editable(self, able: bool = True):
        """当连接建立后，部分选项不可再修改"""
        self.__ui.ProtocolTypeComboBox.setDisabled(not able)
        self.__ui.MyHostAddrLineEdit.setDisabled(not able)
        self.__ui.MyPortLineEdit.setDisabled(not able)

    def serial_editable(self,able:bool=True):
        """串口打开后，参数不可修改"""
        self.__ui.serialPortcomboBox.setDisabled(not able)
        self.__ui.baudRatecomboBox.setDisabled(not able)
        self.__ui.dataBitcomboBox.setDisabled(not able)
        self.__ui.checkBitcomboBox.setDisabled(not able)
        self.__ui.stopBitcomboBox.setDisabled(not able)

    def protocol_type_combobox_handler(self, p_type):
        """ProtocolTypeComboBox的槽函数"""
        self.protocol_type = p_type
        if self.protocol_type == "Web Server":
            self.__ui.SendPlainTextEdit.setPlainText("请打开index.html所在的文件路径")
            self.__ui.SendPlainTextEdit.setEnabled(False)
            self.__ui.OpenFilePushButton.setText("选择路径")
        else:
            # 恢复发送输入框可用
            self.__ui.SendPlainTextEdit.setEnabled(True)
            self.__ui.SendPlainTextEdit.clear()
            self.__ui.OpenFilePushButton.setText("打开文件")
        #切换TCP 客户端与服务器显示
        if self.protocol_type == "TCP Server":
            self.__ui.MyHostAddrLabel.setText('本地IP地址')
            self.__ui.MyPortLabel.setText("本地端口号")
        elif self.protocol_type == "TCP Client":
            self.__ui.MyHostAddrLabel.setText('服务器IP地址')
            self.__ui.MyPortLabel.setText("服务器端口")


    def click_link_handler(self):
        """连接按钮连接时的槽函数"""
        def get_int_port(port):
            # 用户未输入端口则置为-1
            return -1 if port == "" else int(port)

        if self.protocol_type=="TCP Server":
            server_flag =True
            my_port = get_int_port(self.__ui.MyPortLineEdit.text())
            self.editable(False)
            if my_port == -1 :
                mb = QMessageBox(QMessageBox.Critical, "错误", "请输入端口", QMessageBox.Ok, self)
                mb.open()
                self.editable(True)
                self.__ui.ConnectButton.setChecked(False)
                return None

        if self.protocol_type=="TCP Client":
            server_flag = False
            target_ip = str(self.__ui.MyHostAddrLineEdit.text())
            target_port = get_int_port(self.__ui.MyPortLineEdit.text())
            self.editable(False)
            if target_port == -1 and target_ip != "":
                input_d = PortInputDialog(self)
                input_d.setWindowTitle("服务启动失败")
                input_d.setLabelText("请输入目标端口号作为Client启动，或取消")
                input_d.intValueSelected.connect(
                    lambda val: self.__ui.MyPortLineEdit.setText(str(val))
                )
                input_d.open()
                self.editable(True)
                self.__ui.ConnectButton.setChecked(False)
                # 提前终止槽函数
                return None
            elif target_port != -1 and target_ip == "":
                mb = QMessageBox(
                    QMessageBox.Critical, "Client启动错误", "请输入目标IP地址", QMessageBox.Ok, self
                )
                mb.open()
                self.editable(True)
                self.__ui.ConnectButton.setChecked(False)
                # 提前终止槽函数
                return None

        if self.protocol_type == "Web Server" and not self.dir:
            # 处理用户未选择工作路径情况下连接网络
            self.dir = QFileDialog.getExistingDirectory(self, "选择index.html所在路径", "./")
            if self.dir:
                self.__ui.SendPlainTextEdit.clear()
                self.__ui.SendPlainTextEdit.appendPlainText(str(self.dir))
                self.__ui.SendPlainTextEdit.setEnabled(False)
            else:
                self.__ui.ConnectButton.setChecked(False)
                return None

        if self.protocol_type == "TCP Server" and server_flag:
            self.link_signal.emit((self.ServerTCP, "", my_port))
            self.link_flag = self.ServerTCP
            self.__ui.StateLabel.setText("TCP服务端")
        elif self.protocol_type == "TCP Client" and not server_flag:
            self.link_signal.emit((self.ClientTCP, target_ip, target_port))
            self.link_flag = self.ClientTCP
            self.__ui.StateLabel.setText("TCP客户端")
        elif self.protocol_type == "UDP" and server_flag:
            self.link_signal.emit((self.ServerUDP, "", my_port))
            self.link_flag = self.ServerUDP
            self.__ui.StateLabel.setText("UDP服务端")
            # TODO 作为UDP服务端时禁用发送
        elif self.protocol_type == "UDP" and not server_flag:
            self.link_signal.emit((self.ClientUDP, target_ip, target_port))
            self.link_flag = self.ClientUDP
            self.__ui.StateLabel.setText("UDP客户端")
        elif self.protocol_type == "Web Server" and server_flag and self.dir:
            self.link_signal.emit((self.WebServer, "", my_port))
            self.link_flag = self.WebServer
            self.__ui.StateLabel.setText("Web server")

    def serial_click_link_handler(self):
        """串口打开按钮打开处理槽函数"""
        port=self.__ui.serialPortcomboBox.currentText()
        self.serial_editable(False)
        if port=='':
            mb = QMessageBox(
                QMessageBox.Critical, "串口错误", "请选择有效串口", QMessageBox.Ok, self
            )
            mb.open()
            self.editable(True)
            self.__ui.openButton.setChecked(False)
            # 提前终止槽函数
            return None
        baud=int(self.__ui.baudRatecomboBox.currentText())
        databit=int((self.__ui.dataBitcomboBox.currentText())[0])
        checkbit=self.ParityDic[self.__ui.checkBitcomboBox.currentText()]
        stopbit=self.StopbitDic[self.__ui.stopBitcomboBox.currentText()]
        self.seri_link_signal.emit((self.SeriPort,port,baud,databit,checkbit,stopbit))
        self.link_flag=self.SeriPort
        self.__ui.StateLabel.setText("Serial port")

    def send_link_handler(self):
        """
        SendButton控件点击触发的槽
        """
        if self.link_flag != self.NoLink:
            loop_flag = self.__ui.LoopSendCheckBox.checkState()  # 循环发送标识
            send_msg = self.__ui.SendPlainTextEdit.toPlainText()
            if loop_flag == 0:
                self.send_signal.emit(send_msg)
                self.__ui.SendPlainTextEdit.setPlainText('') #清空已发送内容
                self.__ui.SendPlainTextEdit.textCursor()
            elif loop_flag == 2:
                send_timer = QTimer(self)
                send_timer.start(int(self.__ui.LoopSendSpinBox.value()))
                send_timer.timeout.connect(lambda: self.send_signal.emit(send_msg))
                self.__ui.LoopSendCheckBox.stateChanged.connect(
                    lambda val: send_timer.stop() if val == 0 else None
                )
                self.__ui.ConnectButton.toggled.connect(
                    lambda val: None if val else send_timer.stop()
                )  # 断开连接停止计时

    def msg_write(self, msg: str):
        """将提示消息写入ReceivePlainTextEdit"""
        # 显示接收时间,包含毫秒显示
        currTime=datetime.datetime.now().strftime('%H:%M:%S.%f')
        msg_time=currTime+msg
        if self.receive_show_flag:
            self.__ui.ReceivePlainTextEdit.appendPlainText(msg_time)

    def info_write(self, info: str, mode: int):
        """
        将接收到或已发送的消息写入ReceivePlainTextEdit
        :param info: 接收或发送的消息
        :param mode: 模式，接收/发送
        :return: None
        """
        if self.receive_show_flag:
            if mode == self.InfoRec:
                if self.receive_HEX_flag:  # 以十六进制接收
                    info=bytes(info,encoding='utf-8') #转换成bytes类型
                    info_hex = base64.b16encode(info) #16进制编码
                else:
                    info_hex = info

                self.__ui.ReceivePlainTextEdit.appendHtml(
                    f'<font color="blue">{info_hex}</font>'
                )
                self.ReceiveCounter += 1
                self.counter_signal.emit(self.SendCounter, self.ReceiveCounter)
            elif mode == self.InfoSend:
                if self.send_HEX_flag: #以十六进制发送
                    info_hex=base64.b16encode(info.encode())
                else:
                    info_hex=info
                self.__ui.ReceivePlainTextEdit.appendHtml(
                    f'<font color="green">{info_hex}</font>'
                )
            self.__ui.ReceivePlainTextEdit.appendHtml("\n")
        else:
            if mode == self.InfoRec:
                self.ReceiveCounter += 1
                self.counter_signal.emit(self.SendCounter, self.ReceiveCounter)

    def click_disconnect(self):
        self.disconnect_signal.emit()
        self.link_flag = self.NoLink
        self.__ui.StateLabel.setText("未连接")


    def counter_signal_handler(self, send_count, receive_count):
        """控制收发计数器显示变化的槽函数"""
        self.__ui.SendCounterLabel.setText(str(send_count))
        self.__ui.ReceiveCounterLabel.setText(str(receive_count))

    def counter_reset_button_handler(self):
        """清零收发计数器的槽函数"""
        self.SendCounter = 0
        self.ReceiveCounter = 0
        self.counter_signal.emit(self.SendCounter, self.ReceiveCounter)

    def open_file_handler(self):
        if self.link_flag in [self.ServerTCP, self.ClientTCP, self.ClientUDP]:
            # 打开文本文件，加载到发送PlainTextEdit
            def read_file(file_dir):
                if file_dir:
                    try:
                        with open(file_dir, "r", encoding="UTF8") as f:
                            self.__ui.SendPlainTextEdit.clear()
                            self.__ui.SendPlainTextEdit.appendPlainText(f.read())
                    except UnicodeDecodeError:
                        #  如果不能用UTF8解码
                        mb = QMessageBox(
                            QMessageBox.Critical,
                            "无法读取文件",
                            "无法读取文件，请检查输入",
                            QMessageBox.Ok,
                            self,
                        )
                        mb.open()

            fd = QFileDialog(self, "选择一个文件", "./", "文本文件(*, *)")
            fd.setAcceptMode(QFileDialog.AcceptOpen)
            fd.setFileMode(QFileDialog.ExistingFile)
            fd.fileSelected.connect(read_file)
            fd.open()

        elif self.link_flag == self.NoLink and self.protocol_type == "Web Server":
            self.dir = QFileDialog.getExistingDirectory(self, "选择index.html所在路径", "./")
            self.__ui.SendPlainTextEdit.clear()
            self.__ui.SendPlainTextEdit.appendPlainText(str(self.dir))
            self.__ui.SendPlainTextEdit.setEnabled(False)

    def r_save_data_button_handler(self):
        """接收设置保存数据按键的槽函数"""
        text = self.__ui.ReceivePlainTextEdit.toPlainText()
        file_name = QFileDialog.getSaveFileName(
            self, "保存到txt", "./", "ALL(*, *);;txt文件(*.txt)", "txt文件(*.txt)"
        )[0]
        try:
            with open(file_name, mode="w") as f:
                f.write(text)
        except FileNotFoundError:
            pass  # 如果用户取消输入，filename为空，会出现FileNotFoundError

    def receive_pause_checkbox_toggled_handler(self, ste: bool):
        """暂停接受复选框的槽函数"""
        if ste:
            self.receive_show_flag = False
        else:
            self.receive_show_flag = True

    def send_HEX_checkbox_toggled_handler(self,ste:bool):
        """以十六进制发送的复选框的槽函数"""
        if ste:
            self.send_HEX_flag=True
        else:
            self.send_HEX_flag=False
    def receive_HEX_checkbox_toggled_handler(self,ste:bool):
        """以十六进制接收的复选框的槽函数"""
        if ste:
            self.receive_HEX_flag=True
        else:
            self.receive_HEX_flag=False


    def changeEvent(self, a0: QtCore.QEvent):
        """重写最小化事件，直接隐藏到托盘"""
        if a0.type() == QtCore.QEvent.WindowStateChange:
            self.hide()

    NoLink = -1
    ServerTCP = 0
    ClientTCP = 1
    ServerUDP = 2
    ClientUDP = 3
    WebServer = 4
    SeriPort=5
    InfoSend = 0
    InfoRec = 1


 # 最小化到托盘
class TrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, MainWindow, parent=None):
        super(TrayIcon, self).__init__(parent)
        self.ui = MainWindow
        self.createMenu()

    def createMenu(self):
        self.menu = QtWidgets.QMenu()
        self.showAction1 = QtWidgets.QAction("启动", self, triggered=self.show_window)
        self.quitAction = QtWidgets.QAction("退出", self, triggered=self.quit)

        self.menu.addAction(self.showAction1)
        self.menu.addAction(self.quitAction)
        self.setContextMenu(self.menu)

        # 设置图标
        self.setIcon(QtGui.QIcon("./UI/Icons/Network.png"))
        self.icon = self.MessageIcon()

        # 把鼠标点击图标的信号和槽连接
        self.activated.connect(self.onIconClicked)

    def show_window(self):
        # 若是最小化，则先正常显示窗口，再变为活动窗口（暂时显示在最前面）
        self.ui.showNormal()
        self.ui.activateWindow()

    def quit(self):
        self.setVisible(False)
        QtWidgets.qApp.quit()

    # 鼠标点击icon传递的信号会带有一个整形的值，1是表示单击右键，2是双击，3是单击左键，4是用鼠标中键点击
    def onIconClicked(self, reason):
        if reason == 2 or reason == 3:
            # self.showMessage("Message", "skr at here", self.icon)
            if self.ui.isMinimized() or not self.ui.isVisible():
                # 若是最小化，则先正常显示窗口，再变为活动窗口（暂时显示在最前面）
                self.ui.showNormal()
                self.ui.activateWindow()
                self.ui.setWindowFlags(QtCore.Qt.Window)
                self.ui.show()
            else:
                # 若不是最小化，则最小化
                self.ui.showMinimized()
                self.ui.setWindowFlags(QtCore.Qt.SplashScreen | QtCore.Qt.FramelessWindowHint )
                self.ui.show()


if __name__ == "__main__":
    import sys

    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = WidgetLogic()

    window.show()
    ti=TrayIcon(window)
    ti.show()
    sys.exit(app.exec_())
