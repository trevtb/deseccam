import ConfigParser


class DesecConfigParser:
    config = None

    def __init__(self):
        self.config = ConfigParser.ConfigParser()
        self.config.read("/etc/deseccam/config.cfg")

    @staticmethod
    def is_float(n):
        try:
            float(n)
            return True
        except ValueError:
            pass

        return False

    def correct_path(self, path):
        if path[-1:] != '/':
            return path + '/'
        else:
            return path

    def getoption(self, section, name):
        option = self.config.get(section, name)
        if option.lower() == 'yes':
            option = True
        elif option.lower() == 'no':
            option = False
        elif option.lstrip("-+").isdigit():
            option = int(option)
        elif self.is_float(option):
            option = float(option)

        return option

    def getsettings(self):
        settings = dict()
        for section in self.config.sections():
            for option in self.config.options(section):
                settings[option] = self.getoption(section, option)
        settings['mddir'] = self.correct_path(settings['mddir'])
        settings['ftpremotedir'] = self.correct_path(settings['ftpremotedir'])
        return settings