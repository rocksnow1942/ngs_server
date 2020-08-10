from mongoengine import (DynamicDocument, StringField,
    ReferenceField, DateTimeField, ListField, CASCADE, DictField, queryset_manager
)

from datetime import datetime , timedelta


class Project(DynamicDocument):
    name = StringField(max_length=1000, required=True, unique=True)
    desc = StringField(max_length=9000, default='A project.')
    # exps = ListField(ReferenceField(Experiment, reverse_delete_rule=PULL))
    created = DateTimeField(default=datetime.now)

    meta = {
        'indexes': ['name'],
        'db_alias': 'echem',
        'ordering': ['-created']
    }

    @property
    def exps(self):
        " load all epxeriments"
        return Experiment.objects(project=self)


class Experiment(DynamicDocument):
    name = StringField(max_length=1000, required=True,)
    author = StringField(max_length=1000)
    note = StringField(max_length=9999)
    desc = StringField(max_length=9999)
    project = ReferenceField('Project',reverse_delete_rule=CASCADE)
    # data = ListField(ReferenceField(EchemData,reverse_delete_rule=PULL))
    
    created = DateTimeField(default=datetime.now)

    meta = {
        'indexes': [
            {
                'fields': ['$name','$author','$note','$desc'],
                'default_language':'english',
                'weights': {'name':10, 'note': 5, 'desc': 5, 'author': 5,}
            }
        ],
        'db_alias': 'echem',
        'ordering': ['-created'],
    }

    @queryset_manager
    def recent(self, queryset):
        return queryset.filter(created__gte=datetime.now()-timedelta(days=7))
    
    @property
    def data(self):
        " load all epxeriments"
        return EchemData.objects(exp=self)



class EchemData(DynamicDocument):
    """
    dtype = covid-trace
    name: 
    desc: 
    exp: 
    author:
    data : {
        time: [timestamp,...]
        rawdata: [[v,a],[...]]
        fit:[{fx:,fy:,pc:,pv:,err:,},...]
    }
    """
    DTYPE = ['covid-trace', 'device-trace' ]
    dtype = StringField(max_length=100, choices=DTYPE)
    name = StringField(max_length=1000)
    desc = StringField(max_length=1000)
    author = StringField(max_length=100)
    data = DictField()
    exp = ReferenceField('Experiment', reverse_delete_rule=CASCADE)
    created = DateTimeField(default=datetime.now)
    
    meta = {
        'indexes': [
            {
                'fields': ['$name', '$desc', '$dtype'],
                'default_language':'english',
                'weights': {'name': 10,  'desc': 5,  'dtype': 4}
            }
        ],
        'db_alias': 'echem',
        'ordering': ['-created'],
    }




mongomodels = {'exp': Experiment, 'eProject': Project,'eData':EchemData}
