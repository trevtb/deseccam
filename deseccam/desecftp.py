import ftplib
import datetime
import time
import socket
import os


class FTPSyncdaemon:
    loggq = None
    settings = None
    connection = None
    currentdir = None

    def __init__(self, settings, loggq):
        self.loggq = loggq
        self.settings = settings
        self.settings['ftpcontimeout'] = 20
        self.currentdir = self.settings['ftpremotedir']

    def handle_exit(self):
        ctime = datetime.datetime.now().strftime('%d-%m-%Y, %H:%M:%S')
        self.print_and_log(ctime+': FTP syncronization failed.')
        raise Exception("FTP sync failed.")

    def print_and_log(self, msg):
        print msg
        self.loggq.put(msg)

    def start_loop(self):
        while True:
            if os.path.exists('/etc/deseccam/sync.tmp'):
                self.sync()
                try:
                    self.connection.quit()
                except Exception:
                    pass
                os.remove('/etc/deseccam/sync.tmp')
            time.sleep(self.settings['ftpinterval'])

    def sync(self):
        try:
            ctime = datetime.datetime.now().strftime('%d-%m-%Y, %H:%M:%S')
            self.print_and_log(ctime+': Starting ftp syncronization')
            self.connect()
            self.login()
            localfolders = os.listdir(self.settings['mddir'])
            self.changedir(self.settings['ftpremotedir'])
            remotefolders = self.getdircontent()
            mkfolders = self.compare(localfolders, remotefolders)
            for f in mkfolders:
                self.createdir(f)
            for folder in localfolders:
                loc = os.listdir(self.settings['mddir']+folder)
                self.changedir(self.settings['ftpremotedir']+folder)
                rem = self.getdircontent()
                mkfiles = self.compare(loc, rem)
                for fileh in mkfiles:
                    self.upload(fileh, folder)
            ctime = datetime.datetime.now().strftime('%d-%m-%Y, %H:%M:%S')
            self.print_and_log(ctime+': FTP syncronization finished without errors.')
        except:
            return

    def connect(self):
        try:
            self.connection = ftplib.FTP()
            self.connection.connect(self.settings['ftphost'], self.settings['ftpport'], self.settings['ftpcontimeout'])
        except (socket.error, socket.gaierror), e:
            self.print_and_log('ERROR: cannot reach "%s".' % self.settings['ftphost'])
            self.handle_exit()
            return
        self.print_and_log('*** Connected to host "%s".' % self.settings['ftphost'])

    def login(self):
        try:
            if self.settings['ftpanonymous']:
                self.connection.login()
            else:
                self.connection.login(self.settings['ftpuser'], self.settings['ftppass'])
        except ftplib.error_perm:
            self.print_and_log('ERROR: wrong username or password.')
            self.handle_exit()
            return
        self.print_and_log('*** Logged in as "'+self.settings['ftpuser']+'"')

    def changedir(self, dir):
        try:
            self.connection.cwd(dir)
        except ftplib.error_perm:
            self.print_and_log('ERROR: cannot CD to "%s"' % dir)
            self.handle_exit()
            return
        self.currentdir = dir
        self.print_and_log('*** Changed folder to "%s"' % dir)

    def getdircontent(self):
        log = []
        self.connection.retrlines('LIST', callback=log.append)
        files = (' '.join(line.split()[8:]) for line in log)
        files_list = list(files)

        return files_list

    def createdir(self, dir):
        try:
            self.connection.mkd(self.settings['ftpremotedir'] + dir)
        except ftplib.error_perm:
            self.print_and_log('ERROR: cannot create folder "%s"' % dir)
            self.handle_exit()
            return
        self.print_and_log('*** Created folder "%s"' % dir)

    def compare(self, local, remote):
        tmp = local[:]
        for i in range(len(tmp)):
            for j in range(len(remote)):
                if tmp[i] == remote[j]:
                    tmp[i] = None
        retval = []
        for item in tmp:
            if item is not None:
                retval.append(item)
        return retval

    def upload(self, file, folder):
        try:
            f = open(self.settings['mddir']+folder+'/'+file, 'rb')
            self.connection.storbinary('STOR '+file, f)
            f.close()
        except ftplib.error_perm:
            self.print_and_log('ERROR: Could not upload file "'+file+'" to folder "'+folder+'"')
            self.handle_exit()
            return
        self.print_and_log('*** Uploaded file "'+file+'" to folder "'+folder+'"')