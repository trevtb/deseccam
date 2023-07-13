from multiprocessing import Process, Queue
import deseccamhelper
import desecmotion
import desechttp
import desecftp
import signal
import os
import datetime


class Scheduler:
    config = None
    httpq = None
    mdq = None
    loggq = None
    processes = None
    active = None
    camio = None

    def __init__(self, config, loggq):
        self.config = config
        self.processes = []
        self.loggq = loggq
        self.active = False
        if not self.config['enablemd']:
            self.camio = deseccamhelper.CamIO(self.config['resolution'], self.config['portnum'], self.config['saturation'])

    def signal_handler(self, signal, _stack_frame):
        pass

    def print_and_log(self, msg):
        print msg
        self.loggq.put(msg)

    def createprocess(self, pstype, isprocess=False, settings=None, arg1=None, arg2=None, arg3=None):
        if not isprocess:
            if pstype == 'http':
                self.httpq = Queue()
                p = Process(target=self.createprocess, args=(pstype, True, self.config,
                                                         self.httpq, os.getpid(), self.loggq))
            elif pstype == 'md':
                self.mdq = Queue()
                p = Process(target=self.createprocess, args=(pstype, True, self.config, self.mdq, self.loggq))
            else:
                p = Process(target=self.createprocess, args=(pstype, True, self.config, self.loggq))

            p.daemon = True
            p.start()
            self.processes.append(p)
        elif isprocess:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)

            if pstype == 'md':
                desecmotion.DesecMotionDetector(settings, arg1, arg2).start_loop()
            elif pstype == 'http':
                desechttp.ThreadedHTTP(settings['interface'], settings['port'], settings['onlylocalhost'],
                                       settings['useauthentication'], settings['useaccessprotection'],
                                       settings['allowedip'], settings['username'],
                                       settings['password'], arg1, arg2, arg3).start_loop()
            elif pstype == 'ftp':
                desecftp.FTPSyncdaemon(settings, arg1).start_loop()

    def shutdownall(self):
        self.active = False
        if self.httpq is not None:
            self.httpq.close()
        if self.mdq is not None:
            self.mdq.close()
        for p in self.processes:
            os.system('kill -9 {0}'.format(p.pid))

    def run(self):
        self.active = True
        # Check if the camera is available
        if not deseccamhelper.CamIO.camavailable(self.config['portnum']):
            raise Exception('No camera detected, exiting. (Code: 05)')

        ctime = datetime.datetime.now().strftime('%d-%m-%Y, %H:%M:%S')
        self.print_and_log(ctime+": Starting server.")
        if self.config['enablemd']:
            self.createprocess('md')
            self.print_and_log("[OK] MotionDetection module started.")
        if self.config['enablehttp']:
            self.createprocess('http')
            self.print_and_log("[OK] HTTP module started.")
        if self.config['enableftp']:
            self.createprocess('ftp')
            self.print_and_log("[OK] FTP module started.")

        self.print_and_log("Server started successfully.")

        while self.active:
            if self.config['enablemd']:
                img = self.mdq.get()
            else:
                img = self.camio.getimage()
            if self.config['enablehttp'] and self.httpq.empty():
                self.httpq.put(img)
