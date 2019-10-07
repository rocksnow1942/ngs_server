
from app import db

from flask_login import UserMixin, current_user

from flask import current_app

import json
from sqlalchemy import Column, String, ForeignKey, DateTime, func, ForeignKey
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import relationship

def JSON_descriptor(name):
    class Desc():
        def __get__(self,instance,cls):
            return json.loads(getattr(instance,name))

        def __set__(self,instance,value):
            setattr(instance,name,json.dumps(value))
        
        def __delete__(self,instance):
            setattr(instance, name, json.dumps({}))
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
    def meta_json(self):
        return json.loads(self._meta)

    @property
    def raw_json(self):
        return json.loads(self._data)

    @property
    def index(self):
        return self.__repr__()

    @staticmethod
    def sync_obj(key,newkey=None,meta={},raw={}):
        exp_id,run = key.split('-')
        u = Plojonior_Data.query.get((exp_id, run))
        try:
            if not u:
                u = Plojonior_Data(exp_id=exp_id,run=run)
                db.session.add(u)
            if newkey:
                u.exp_id,u.run = newkey.split('-')
            if meta:
                u.meta=meta
            if raw: 
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
