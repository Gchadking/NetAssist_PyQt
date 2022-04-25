import sys
import win32api
import win32event
from winerror import ERROR_ALREADY_EXISTS
from PyQt5.QtWidgets import QApplication

from MainWindowLogic import WidgetLogic,TrayIcon
from Network import NetworkLogic


class CommonHelper:
    def __init__(self):
        pass

    @staticmethod
    def read_qss(style):
        """读取QSS样式表的方法"""
        with open(style, "r") as f:
            return f.read()

class MainWindow(WidgetLogic, NetworkLogic):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.link_signal.connect(self.link_signal_handler)
        self.seri_link_signal.connect(self.seri_link_signal_handler)
        self.disconnect_signal.connect(self.disconnect_signal_handler)
        self.send_signal.connect(self.send_signal_handler)
        self.tcp_signal_write_msg.connect(self.msg_write)
        self.tcp_signal_write_info.connect(self.info_write)
        self.udp_signal_write_msg.connect(self.msg_write)
        self.udp_signal_write_info.connect(self.info_write)
        self.signal_write_msg.connect(self.msg_write)
        self.serp_signal_write_msg.connect(self.msg_write)
        self.serp_signal_write_info.connect(self.info_write)

    def link_signal_handler(self, signal) -> None:
        """
        连接信号分用的槽函数
        """
        link_type, target_ip, port = signal
        if link_type == self.ServerTCP:
            self.tcp_server_start(port)
        elif link_type == self.ClientTCP:
            self.tcp_client_start(target_ip, port)
        elif link_type == self.ServerUDP:
            self.udp_server_start(port)
        elif link_type == self.ClientUDP:
            self.udp_client_start(target_ip, port)
        elif link_type == self.WebServer:
            self.web_server_start(port)


    def seri_link_signal_handler(self,signal):
        """串口连接信号用的槽函数"""
        linktype,seriport, baud, databit, checkbit, stopbit = signal
        self.serial_port_open(seriport, baud, databit, checkbit, stopbit)

    def disconnect_signal_handler(self) -> None:
        """断开连接的槽函数"""
        if self.link_flag == self.ServerTCP or self.link_flag == self.ClientTCP:
            self.tcp_close()
        elif self.link_flag == self.ServerUDP or self.link_flag == self.ClientUDP:
            self.udp_close()
        elif self.link_flag == self.WebServer:
            self.web_close()
        elif self.link_flag ==self.SeriPort:
            self.serial_port_close()

    def send_signal_handler(self, msg: str) -> None:
        """发送按钮的槽函数"""
        if self.link_flag == self.ServerTCP or self.link_flag == self.ClientTCP:
            self.tcp_send(msg)
            self.SendCounter += 1
        elif self.link_flag == self.ClientUDP:
            self.udp_send(msg)
            self.SendCounter += 1
        elif self.link_flag == self.SeriPort:
            self.write(msg)
            self.SendCounter+=1
        self.counter_signal.emit(self.SendCounter, self.ReceiveCounter)

    def closeEvent(self, event) -> None:
        """
        重写closeEvent方法，实现MainWindow窗体关闭时执行一些代码
        :param event: close()触发的事件
        """
        self.disconnect_signal_handler()


if __name__ == "__main__":
    mutexname = "网络助手"  # 互斥体命名
    mutex = win32event.CreateMutex(None, False, mutexname) #只允许同时运行一个程序
    if (win32api.GetLastError() == ERROR_ALREADY_EXISTS):
        print('程序已启动')
        exit(0)

    app = QApplication(sys.argv)
    QApplication.setQuitOnLastWindowClosed(False) #关闭按钮不退出程序，托盘最小化
    window = MainWindow()
    styleFile = "./Style/qss/flat_white.qss"
    import Style.qss_rc  # 导入资源

    qssStyle = CommonHelper.read_qss(styleFile)
    window.setStyleSheet(qssStyle)
    window.show()
    ti = TrayIcon(window) #最小化到托盘
    ti.show()
    sys.exit(app.exec_())
