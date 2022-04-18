from datetime import datetime
from itertools import permutations, product
from pathlib import Path
from urllib.parse import urlparse
import os
import yaml

_ENV = os.environ.get("RF_ENV", "DEV")


class AttrDict(dict):
    def __init__(self, d=None):
        super().__init__()
        if d:
            for k, v in d.items():
                self.__setitem__(k, v)

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            value = AttrDict(value)
        super().__setitem__(key, value)

    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)

    __setattr__ = __setitem__


class Config:
    def __init__(self, file_name, env):
        self.__env = env
        with open(file_name) as fp:
            self.__config = AttrDict(yaml.safe_load(fp))[self.__env]

    def __getattr__(self, attr):
        return self.__config.get(attr)

    def __getitem__(self, item):
        return self.__config.get(item)

    def __contains__(self, item):
        return item in self.__config


class AppConfig(Config):
    def __init__(self, file_name, env):
        super().__init__(file_name, env)

    @property
    def firebase_address(self) -> str:
        return self.firebase_address


cfg = AppConfig(Path(__file__).parent / "config.yml", _ENV)
