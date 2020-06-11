from mongoengine import * 
from datetime import datetime 


class EchemData(Document):
    name = StringField(max_length=1000, required=True)
    created = DateTimeField(default=datetime.now)

    meta = {
        'db_alias':'buglogger'
    }



class Experiment(Document):
    name = StringField(max_length=1000, required=True)
    tag = StringField(max_length=1000)
    note = StringField(max_length=9999)
    dataType = StringField(max_length=100)
    data = DictField()
    timepoint = ListField()

    created = DateTimeField(default=datetime.now)

    meta = {
        'indexes': ['name'],
        'db_alias': 'test'
    }


class Project(Document):
    name = StringField(max_length=1000, required=True)
    desc = StringField(max_length=9000, required=True)
    created = DateTimeField(default=datetime.now)
    

mongomodels = {'exp': Experiment, 'echem': EchemData}
