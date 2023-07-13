import datetime
import sys
import os
import errno
import time
import deseccamhelper
import desecmail
from threading import Thread


class DesecMotionDetector:
    q = None
    loggq = None
    settings = None
    t_minus = None
    t = None
    t_plus = None
    lastmd = None
    comparetimeout = 120
    mailtimeout = 300
    camio = None

    def __init__(self, settings, q, loggq):
        self.q = q
        self.loggq = loggq
        self.settings = settings
        self.camio = deseccamhelper.CamIO(self.settings['resolution'], self.settings['portnum'], self.settings['saturation'])

    def print_and_log(self, msg):
        print msg
        self.loggq.put(msg)

    def start_loop(self):
        self.t_minus = self.camio.getimage()
        self.t = self.camio.getimage()
        self.t_plus = self.camio.getimage()

        while True:
            dimg = deseccamhelper.CamIO.diffimg(self.t_minus, self.t, self.t_plus)

            # Write images if motion is detected
            if deseccamhelper.CamIO.getvalidpixels(dimg) > self.settings['movthreshold']:
                th = datetime.datetime.now()
                self.print_and_log(th.strftime('%d-%m-%Y, %H:%M:%S') + ": Motion detected.")
                if self.lastmd is None:
                    self.lastmd = datetime.datetime.now() - datetime.timedelta(seconds=(10*self.comparetimeout))
                Thread(target=self.handle_motion_detected, args=(self.settings, self.loggq, th, self.lastmd,
                                                                 self.comparetimeout, self.mailtimeout, self.t)).start()
                self.lastmd = th
            # Read next image
            self.t_minus = self.t
            self.t = self.t_plus
            self.t_plus = self.camio.getimage()

            if self.q.empty():
                self.q.put(self.t_plus)

    def handle_motion_detected(self, settings, lq, time_handle, ld, comptimeout, mtimeout, jpg):
        MotionHandler(settings, lq, time_handle, ld, comptimeout, mtimeout, jpg).process_motion()


class MotionHandler:
    loggq = None
    settings = None
    time_handle = None
    jpg = None
    lastmd = None
    comparetimeout = None
    mailtimeout = None

    def __init__(self, settings, loggq, time_handle, lastmd, comparetimeout, mailtimeout, jpg):
        self.loggq = loggq
        self.settings = settings
        self.time_handle = time_handle
        self.jpg = jpg
        self.lastmd = lastmd
        self.comparetimeout = comparetimeout
        self.mailtimeout = mailtimeout

    def print_and_log(self, msg):
        print msg
        self.loggq.put(msg)

    def comp_dates(self, past, future):
        diff = future - past
        return diff.total_seconds()

    def clean_up(self):
        folders = os.listdir(self.settings['mddir'])
        for folder in folders:
            cdate = self.modification_date(self.settings['mddir']+folder)
            diff = self.comp_dates(cdate, datetime.datetime.now())
            # if older than one day
            if diff >= 86400:
                dircont = os.listdir(self.settings['mddir']+folder)
                for f in dircont:
                    os.remove(self.settings['mddir']+folder+'/'+f)
                os.rmdir(self.settings['mddir']+folder)

    def process_motion(self):
        dirname = self.settings['mddir']+self.time_handle.strftime('%d-%m-%Y')
        if not os.path.isdir(dirname):
            try:
                os.makedirs(dirname)
            except OSError as exception:
                if exception.errno != errno.EEXIST:
                    sys.exit(0)
                pass
        deseccamhelper.CamIO.writeimg(dirname + '/' +
                                      self.time_handle.strftime('%d%m%Y_%Hh%Mm%Ss%f') + '.jpg',
                                      self.jpg)
        if not os.path.exists('/etc/deseccam/sync.tmp') \
                and self.comp_dates(self.lastmd, self.time_handle) >= self.comparetimeout:
                file = open('/etc/deseccam/sync.tmp', "w+")
                file.write("1")
                file.close()
        if self.settings['enablemail'] and self.comp_dates(self.lastmd, self.time_handle) >= self.mailtimeout:
            time.sleep(3)
            self.mail_notify()

    def modification_date(self, dirname):
        t = os.path.getmtime(dirname)
        return datetime.datetime.fromtimestamp(t)

    def mail_notify(self):
        dirname = self.time_handle.strftime('%d-%m-%Y')
        files = os.listdir(self.settings['mddir']+dirname)
        sfiles = []
        for f in files:
            ctime = self.modification_date(self.settings['mddir']+dirname+'/'+f)
            now = datetime.datetime.now()
            diff = self.comp_dates(ctime, now)
            # Only add files created 10 minutes or less ago
            if diff <= self.mailtimeout:
                sfiles.append(dirname+'/'+f)
        mailer = desecmail.Mailer(self.settings, self.time_handle, sfiles)
        ctime = datetime.datetime.now().strftime('%d-%m-%Y, %H:%M:%S')
        if not mailer.deliver():
            self.print_and_log(ctime+": ERROR while trying to send mail. Please check the mail settings.")
        else:
            self.print_and_log(ctime+": Successfully sent notification mail.")