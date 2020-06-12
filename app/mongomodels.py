from mongoengine import * 
from datetime import datetime 





class Experiment(DynamicDocument):
    name = StringField(max_length=1000, required=True, unique=True)
    tag = StringField(max_length=1000)
    author = StringField(max_length=1000)
    note = StringField(max_length=9999)
    desc = StringField(max_length=9999)
    dataType = StringField(max_length=100)
    data = DictField()
    
    created = DateTimeField(default=datetime.now)

    meta = {
        'indexes': ['name'],
        'db_alias': 'echem'
    }


class Project(DynamicDocument):
    name = StringField(max_length=1000, required=True, unique=True)
    desc = StringField(max_length=9000, default='A project.')
    exps = ListField(ReferenceField(Experiment, reverse_delete_rule=PULL))
    created = DateTimeField(default=datetime.now)

    meta = {
        'indexes': ['name'],
        'db_alias': 'echem'
    }
    

mongomodels = {'exp': Experiment, 'eProject': Project}
