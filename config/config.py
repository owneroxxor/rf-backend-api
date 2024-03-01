from envyaml import EnvYAML


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
        self.__config = AttrDict(EnvYAML(file_name, strict=False).export())[self.__env]

    def __getattr__(self, attr):
        return self.__config.get(attr)

    def __getitem__(self, item):
        return self.__config.get(item)

    def __contains__(self, item):
        return item in self.__config


class AppConfig(Config):
    def __init__(self, file_name, env):
        super().__init__(file_name, env)
