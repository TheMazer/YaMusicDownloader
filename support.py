import configparser
import random


class Config:
    def __init__(self, path = 'config.ini'):
        self.path = path
        self.config = configparser.ConfigParser()
        self.config.read(self.path)

    def load(self, path = None):
        self.path = path if path is not None else self.path
        self.config.read(self.path)

    def get(self, key, section = 'Settings'):
        if section is not None:
            try: value = self.config[section][key]
            except KeyError: value = 0
            return value
        else:
            try: value = self.config[key]
            except KeyError: value = 0
            return value

    def set(self, key, value, section = None):
        if section is not None:
            if section not in self.config:
                self.config[section] = {}
            self.config[section][key] = value
        else:
            self.config[key] = value

    def save(self):
        with open(self.path, 'w') as configfile:
            self.config.write(configfile)


def shuffleString(s):
    s_list = list(s)
    random.shuffle(s_list)
    return ''.join(s_list)