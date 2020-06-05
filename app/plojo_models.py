from app import db
import json
from sqlalchemy import Column, String, ForeignKey,ForeignKey
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import relationship

def JSON_descriptor(name):
    class Desc():
        def __get__(self,instance,cls):
            return json.loads(getattr(instance,name))

        def __set__(self,instance,value):
            setattr(instance, name, json.dumps(value, separators=(',', ':')))
        
        def __delete__(self,instance):
            setattr(instance, name, json.dumps({}, separators=(',', ':')))
    return Desc()

class Plojonior_Data(db.Model):
    __tablename__ = 'plojo_nior_data'
    exp_id = Column(String(20), ForeignKey('plojo_nior_index.exp'),primary_key=True, )
    run = Column(String(20),primary_key=True)
    _meta = Column(mysql.TEXT)
    _data = Column(mysql.LONGTEXT)
    meta = JSON_descriptor('_meta')
    raw = JSON_descriptor('_data')

    def __repr__(self):
        return f"{self.exp_id}-{self.run}"

    @property
    def index(self):
        return self.__repr__()

    @staticmethod
    def sync_obj(key,newkey=None,meta=None,raw=None):
        exp_id,run = key.split('-')
        u = Plojonior_Data.query.get((exp_id, run))
        try:
            if not u:
                u = Plojonior_Data(exp_id=exp_id,run=run)
                db.session.add(u)
            if newkey!=None:
                u.exp_id,u.run = newkey.split('-')
            if meta!=None:
                u.meta=meta
            if raw!=None: 
                u.raw=raw
            db.session.commit()
        except Exception as e:
            print(e)
                  
class Plojonior_Index(db.Model):
    __tablename__ = 'plojo_nior_index'
    exp = Column(String(20), primary_key=True)
    name = Column(String(500))
    date = Column(String(20))
    author = Column(String(20))
    tag = Column(String(500))
    runs = relationship('Plojonior_Data', backref='exp', cascade="save-update, delete")

    @property
    def jsonify(self):
        return {'name':self.name,'date':self.date,'author':self.author,'tag':self.tag}

    @staticmethod
    def sync_obj(key, value):
        u = Plojonior_Index.query.get(key)
        if not u:
            u = Plojonior_Index(exp=key)
            db.session.add(u)
        for k,i in value.items():
            setattr(u,k,i)
        db.session.commit()

class Plojo_Data(db.Model):
    __tablename__ = 'plojo_data'
    index = Column(String(300), primary_key=True)
    _data = Column(mysql.TEXT)
    data = JSON_descriptor('_data')

    def __repr__(self):
        return f"{self.index}"

    @staticmethod
    def sync_obj(key, data=None):
        u = Plojo_Data.query.get(key)
        try:
            if not u:
                u = Plojo_Data(index=key)
                db.session.add(u)
            if data!=None:
                u.data = data
            db.session.commit()
        except Exception as e:
            print(e)
    
    @staticmethod
    def next_index( ):
        entry = [i[0] for i in db.session.query(Plojo_Data.index).all()]
        if not entry:
            entry_start = 0
        else:
            entry = sorted(entry, key=lambda x: int(x.split('-')[0][3:]))[-1]
            entry_start = int(entry.split('-')[0][3:])+1
        return 'ams'+str(entry_start)


class Plojo_Project(db.Model):
    __tablename__ = 'plojo_project'
    index = Column(String(300), primary_key=True)
    _data = Column(mysql.LONGTEXT)
    data = JSON_descriptor('_data')

    def __repr__(self):
        return f"Project {self.index}"
    
    @staticmethod
    def sync_obj(key,newkey=None, data=None):
        u = Plojo_Project.query.get(key)
        # try:
        if not u:
            u = Plojo_Project(index=key)
            db.session.add(u)
        if data!= None:
            u.data = data
        if newkey!=None:
            u.index=newkey
        db.session.commit()
    
    @staticmethod
    def next_index(projectname):
        allprojects = [i[0]
                       for i in db.session.query(Plojo_Project.index).all()]
        if not allprojects:
            allprojects = ['0']
        allprojects.sort(key=lambda x: int(x.split('-')[0]), reverse=True)
        entry = allprojects[0]
        entry_start = int(entry.split('-')[0])+1
        return str(entry_start) + '-'+projectname

plojo_models = {'pjdata': Plojonior_Data,
                'pjindex': Plojonior_Index, 'pproject': Plojo_Project,'pdata':Plojo_Data}
