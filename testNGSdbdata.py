from server_mapping import slim_models

s= slim_models.Sequence

s.query.get(1).aptamer_seq


import json


class lazyproperty():
    """
    lazy property descriptor class.
    """
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            value = self.func(instance)
            setattr(instance, self.func.__name__, value)
            return value


def data_string_descriptor(name,mode=[]):
    class Data_Descriptor():
        def __get__(self,instance,cls):
            if instance.data.get(name, None) is None:
                print(name)
                setattr(instance,name,mode)
            return instance.data.get(name)

        def __set__(self,instance,value):
            instance.data.update({name:value})

        def __delete__(self,instance):
            instance.data.pop(name)

    return Data_Descriptor


class DataStringMixin():
    @lazyproperty
    def data(self):
        if self.data_string:
            return json.loads(self.data_string)
        else:
            return {}

    def save_data(self):
        self.data_string = json.dumps(self.data, separators=(',', ':'))


class Analysis( DataStringMixin):
    data_string = "{}"
    _rounds = data_string_descriptor('rounds')()

    @property
    def rounds(self):
        return [i for i in self._rounds]


a=Analysis()
a.data

a._rounds=[1,2]
a.save_data()
a.data_string

a.rounds
