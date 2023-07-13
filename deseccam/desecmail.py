import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class Mailer:
    settings = None
    filenames = None
    msg = None
    connection = None

    def __init__(self, settings, mtime, fnames):
        self.settings = settings
        self.settings['mdate'] = mtime.strftime('%d.%m.%Y')
        self.settings['mtime'] = mtime.strftime('%H:%M:%S')
        self.filenames = fnames

    def build_message(self):
        COMMASPACE = ', '
        self.msg = MIMEMultipart()
        self.msg['Subject'] = 'DESEC: Bewegung erkannt'
        self.msg['From'] = self.settings['mailfrom']
        recvs = self.settings['mailto'].split()
        self.msg['To'] = COMMASPACE.join(recvs)
        text ='Das DESEC Sicherheitssystem hat am '\
                            + self.settings['mdate']\
                            + ' um '\
                            + self.settings['mtime']\
                            + ' Uhr eine Bewegung registriert. Die aufgenommenen Bilder befinden sich in dieser E-Mail.'
        self.msg.attach(MIMEText(text))
        for fileh in self.filenames:
            fp = open(self.settings['mddir']+fileh, 'rb')
            img = MIMEImage(fp.read())
            fp.close()
            self.msg.attach(img)

    def connect(self):
        if self.settings['mailssl'] and not self.settings['mailtls']:
            self.connection = smtplib.SMTP_SSL(self.settings['mailhost']+":"+str(self.settings['mailport']))
        else:
            self.connection = smtplib.SMTP(self.settings['mailhost']+":"+str(self.settings['mailport']))
        if self.settings['mailtls']:
            self.connection.starttls()
        if self.settings['mailuser'] != '':
            self.connection.login(self.settings['mailuser'], self.settings['mailpass'])

    def disconnect(self):
        if self.connection is not None:
            self.connection.quit()

    def send_message(self):
        if self.connection is not None:
            self.connection.sendmail(self.settings['mailfrom'], self.settings['mailto'].split(), self.msg.as_string())

    def deliver(self):
        try:
            self.build_message()
            self.connect()
            self.send_message()
            self.disconnect()
        except:
            return False
        return True

