import numpy as np
from matplotlib.figure import Figure
from collections import Counter
from app import db,login
from datetime import datetime,timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, current_user
from hashlib import md5
from time import time
import jwt
from flask import current_app, url_for
from itertools import islice
import json
from sqlalchemy import Column, String,ForeignKey,DateTime,func
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import relationship
from app.utils.ngs_util import convert_id_to_string,reverse_comp
from app.utils.analysis._alignment import lev_distance
from app.utils.folding._structurepredict import Structure
from app.utils.ngs_util import lazyproperty
from app.utils.search import add_to_index, remove_from_index, query_index
import os,gzip
from inspect import signature,_empty
from contextlib import contextmanager

@contextmanager
def dbAutoSession(autocommit=True):
    """
    an context manager, can be used in with statement or used as a decorator.
    must work in an app context
    """
    try:
        yield db.session
        if autocommit:
            db.session.commit()
    except Exception:
        print('***rollback by manager')
        db.session.rollback()
        raise
    finally:
        print('***remove by manager')
        db.session.remove()


def data_string_descriptor(name,mode=[]):
    class Data_Descriptor():
        def __get__(self,instance,cls):
            if instance.data.get(name, None) is None:
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

class SearchableMixin():
    @classmethod
    def search(cls,expression,page,per_page):
        ids, total = query_index(cls.__tablename__,expression,page,per_page)
        if total==0:
            return cls.query.filter_by(id=0),0
        when = [ (k,i) for i,k in enumerate(ids) ]
        return cls.query.filter(cls.id.in_(ids)).order_by(db.case(when,value=cls.id)),total

    @classmethod
    def before_commit(cls,session,*args,**kwargs):
        session._changes = {'add':list(session.new),
        'update':list(session.dirty),
        'delete': list(session.deleted)}


    @classmethod
    def after_commit(cls,session,*args,**kwargs):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None


    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__,obj)

db.event.listen(db.session, 'before_flush', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_flush', SearchableMixin.after_commit)


class User(UserMixin,db.Model,DataStringMixin):
    __tablename__='user'
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email= db.Column(db.String(120), index=True, unique=True)
    privilege = db.Column(db.String(10),default='user')
    password_hash = db.Column(db.String(128))
    data_string = Column(mysql.LONGTEXT, default="{}")
    analysis_cart= data_string_descriptor('analysis_cart')()
    user_setting = data_string_descriptor('user_setting',{})()
    analysis = relationship('Analysis',backref='user')
    slide_cart = data_string_descriptor('slide_cart',[])()
    follow_ppt = data_string_descriptor('follow_ppt',{})()
    bookmarked_ppt = data_string_descriptor('bookmarked_ppt', [])()
    quick_link = data_string_descriptor('quick_link',[])() # format is [(name,url)]

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self,password):
        self.password_hash=generate_password_hash(password)

    def is_following_ppt(self,ppt_id):
        return str(ppt_id) in self.follow_ppt

    @property
    def follow_ppt_update_count(self):
        update = self.follow_ppt_update()
        return sum(len(i) for i in update.values())

    def remove_dead_ppt_link(self):
        slide_cart,bookmarked_ppt = [],[]
        for i in self.slide_cart:
            if Slide.query.get(i):
                slide_cart.append(i)
        for i in self.bookmarked_ppt:
            if Slide.query.get(i):
                bookmarked_ppt.append(i)
        self.slide_cart ,self.bookmarked_ppt = slide_cart,bookmarked_ppt
        for key in list(self.follow_ppt.keys()):
            ppt = PPT.query.get(key)
            if ppt:
                slides = [i.id for i in ppt.slides]
                self.follow_ppt[key] = list(set(self.follow_ppt[key]) & set(slides))
            else:
                self.follow_ppt.pop(key)



    def single_ppt_update_count(self,ppt_id):
        if str(ppt_id) in self.follow_ppt:
            slides = [i.id for i in PPT.query.get(int(ppt_id)).slides]
            new = set(slides) - set(self.follow_ppt[str(ppt_id)])
            return len(new)
        else:
            return 0

    def follow_ppt_update(self):
        update={}
        for k in list(self.follow_ppt.keys()):
            ppt = PPT.query.get(k)
            if ppt:
                slides = [i.id for i in ppt.slides]
                new = set(slides) - set(self.follow_ppt[k])
                if new:
                    update[k]=list(new)
        return update

    @property
    def ngs_per_page(self):
        return self.user_setting.get('ngs_per_page', 10)

    @property
    def thumbnail(self):
        return self.user_setting.get('thumbnail', 'small')

    @property
    def slide_per_page(self):
        return self.user_setting.get('slide_per_page', 40)

    def check_password(self,password):
        if self.password_hash:
            return check_password_hash(self.password_hash,password)

    def avatar(self,size):
        digest=md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    @property
    def slide_cart_count(self):
        return len(self.slide_cart)

    @property
    def follow_ppt_count(self):
        return len(self.follow_ppt)


    def analysis_cart_count(self):
        return len(self.analysis_cart)

    def get_reset_password_token(self,expires_in=600):
        return jwt.encode({'reset_password':self.id,'exp':time()+expires_in},
                current_app.config['SECRET_KEY'],algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    def test_task(self,n):
        job = current_app.task_queue.enqueue(
            "app.tasks.ngs_data_processing.test_worker", n, job_timeout=3600)

    @property
    def isadmin(self):
        return self.privilege=='admin'

    def launch_search(self,seq,table):
        job = current_app.task_queue.enqueue(
            'app.tasks.ngs_data_processing.lev_distance_search', seq, table, job_timeout=3600)
        t = Task(id=job.get_id(), name=f"Lev distance search in <{table}>.")
        db.session.add(t)
        db.session.commit()
        return t.id

class BaseDataModel():
    @property
    def id_display(self):
        return self.id

class Analysis(SearchableMixin,db.Model, DataStringMixin, BaseDataModel):
    __tablename__ = 'analysis'
    __searchable__ = ['name', 'note']
    __searablemethod__ = ['display']
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    name = Column(String(100))
    date = Column(DateTime(), default=datetime.now)
    user_id = Column(db.Integer, ForeignKey('user.id'))
    data_string = Column(db.Text, default="{}")
    note = Column(String(5000))
    _rounds = data_string_descriptor('_rounds')()
    analysis_file = data_string_descriptor('analysis_file','')()
    pickle_file = data_string_descriptor('pickle_file','')()
    task_id = data_string_descriptor('task_id', '')()
    hist = data_string_descriptor('hist',)()
    cluster_para=data_string_descriptor('cluster_para')()
    heatmap=data_string_descriptor('heatmap','')()
    # Order: name, name_link, Seq Iddisplay, Seq Id link, (display,s.id, )
    cluster_table = data_string_descriptor('cluster_table', [])()
    advanced_result=data_string_descriptor('advanced_result',{})()

    def __repr__(self):
        return f"{self.name}, ID {self.id}"

    def create_datareader(self,roundfilter,sequencefilter):
        """
        generate data reader file by round filter and sequence filter function.
        round filter: function input is Rounds instance, return True if satisfy condition.
        sequence filter: funciton input is SeqRound instance
        """
        if not self.id:
            raise ValueError('Need to commit analysis to get id first.')
        analysis_id = str(self.id)
        analysis = self
        filepath = os.path.join(current_app.config['ANALYSIS_FOLDER'], analysis_id)
        dr = DataReader(name=analysis.name, filepath=filepath)
        rounds = list(filter(roundfilter, Rounds.query.all(),))
        analysis._rounds = [i.id for i in rounds]
        create_folder_if_not_exist(filepath)
        dr.load_from_ngs_server(rounds,sequencefilter)
        analysis.analysis_file = os.path.join(analysis_id, dr.save_pickle())
        analysis.pickle_file = os.path.join(analysis_id, dr.save_pickle('_advanced'))
        ch=dr.sequence_count_hist(save=True)
        lh=dr.sequence_length_hist(save=True)
        analysis.hist = [os.path.join(
            analysis_id, ch), os.path.join(analysis_id, lh)]
        analysis.task_id=''
        analysis.cluster_para=''
        analysis.heatmap=''
        analysis.cluster_table=''
        analysis.save_data()
        db.session.commit()
        return "Done."



    def haschildren(self):
        return (current_user.id!=self.user_id)

    def advanced_result_call_para(self,name,default=""):
        result = self.advanced_result.get(name,{}).get('input',None)
        if result==None:
            return default
        return result

    def advanced_result_task_progress(self,name):
        return self.advanced_result.get(name,{}).get('output', {}).get('task',None)

    def advanced_result_text(self,name):
        return self.advanced_result.get(name, {}).get('output', {}).get('text', [])

    def advanced_result_file(self, name):
        return self.advanced_result.get(name, {}).get('output', {}).get('file', [])

    def advanced_result_img(self, name):
        return self.advanced_result.get(name, {}).get('output', {}).get('img', [])

    def init_advanced_task(self, funcname, para):
        if datareader_API_dict[funcname]['multithread']:
            job = current_app.task_queue.enqueue(
                'app.tasks.ngs_data_processing.advanced_task',self.id,funcname,para,job_timeout=3600*10)
            t = Task(id=job.get_id(), name=f"Advanced call {self}.")
            self.advanced_result[funcname]={'input':para,'output':{'task':t.id,'file':[],'text':[],'img':[]}}
            self.save_data()
            db.session.add(t)
            db.session.commit()
            return t
        else:
            try:
                self.advanced_result[funcname]={'input':para,'output':{'task':None,'file':[],'text':[],'img':[]}}
                para = eval(f"dict({para})")
                dr = self.get_advanced_datareader()
                func = getattr(dr, funcname)
                return_annotation = signature(func).return_annotation
                if return_annotation == _empty:
                    return None
                else:
                    _return = return_annotation.split(',')
                    result = func(**para)
                    if len(_return) == 1:
                        result = [result]
                    output = dict(zip(_return, result))
                    self.advanced_result[funcname]['output'].update(output)
                    self.save_data()
                    db.session.commit()
            except Exception as e:
                self.advanced_result[funcname]['output']['text'] = [f"Error: {e}"]
                self.save_data()
                db.session.commit()
            return None



    @property
    def rounds(self):
        return [Rounds.query.get(i) for i in self._rounds]

    def display(self):
        rd = sum(i.totalread for i in self.rounds)
        l1 = f"Analysis : {self.name}"
        l2 = f"Total Rounds : {len(self.rounds)}, Total Read : {rd}"
        l3 = f"User : {self.user.username}, Date : {self.date}"
        l4 = f"Note : {self.note}"
        return l1, l2, l3, l4

    def get_advanced_datareader(self):
        f = os.path.join(
            current_app.config['ANALYSIS_FOLDER'], self.pickle_file)
        return DataReader.load(f)


    @lazyproperty
    def get_datareader(self):
        """
        only used for getting analysis_file (common one), not for pickle_file (_advanced)
        """
        if self.analysis_file:
            f = os.path.join(
                current_app.config['ANALYSIS_FOLDER'], self.analysis_file)
            return DataReader.load(f)

    def load_rounds(self):
        job = current_app.task_queue.enqueue('app.tasks.ngs_data_processing.load_rounds',self.id,job_timeout=3600*10)
        t = Task(id=job.get_id(),name=f"Load analysis {self}.")
        self.task_id=t.id
        self.save_data()
        db.session.add(t)
        db.session.commit()
        return t

    def build_cluster(self):
        job = current_app.task_queue.enqueue(
            'app.tasks.ngs_data_processing.build_cluster', self.id,job_timeout=3600*10)
        t = Task(id=job.get_id(), name=f"Build cluster {self}.")
        self.task_id = t.id
        self.save_data()
        db.session.add(t)
        db.session.commit()
        return t

    def clustering_parameter(self):
        # default is in the order of distance/lower bd/ upper bd/ count threshold
        if self.cluster_para:
            l1=f"Distance: {self.cluster_para[0]}"
            l2 = f"Sequence Length Lower Boundary: {self.cluster_para[1]}"
            l3 = f"Sequence Length Upper Boundary: {self.cluster_para[2]}"
            l4 = f"Sequence Count Threshold: {self.cluster_para[3]}"
            return l1,l2,l3,l4
        else:
            return []

    def task_type(self):
        if self.task_id:
            task=Task.query.get(self.task_id).name
            return task.split()[0]

    @property
    def clustered(self):
        return bool(self.cluster_para) and (not self.task_id)

    def top_clusters(self):
        # result is list of tuple, in order of: C1/V33.1 , C1, Sequence, similarto ks, distance
        dr=self.get_datareader
        similaritythreshold=10
        if dr:
            topcluster=dr.plot_pie(50, plot=False, translate=False).drop(
                labels='Others', axis=0).index.tolist()
            result = []
            ks = KnownSequence.query.all()
            for i in topcluster:
                a = bool(dr.alias.get(i, 0))*f" / {dr.alias.get(i,0)}"
                repseq=dr[i].rep_seq().replace('-','')
                seq=Sequence.query.filter_by(aptamer_seq=repseq).first()
                ksdistance = [lev_distance(repseq,i.rep_seq,similaritythreshold+abs(i.length-len(repseq))) for i in ks]
                similarity = sorted([(i,j) for i,j in zip(ks,ksdistance)],key=lambda x: x[1])
                similarity = [(ks, i) for ks, i in similarity if i <= (similaritythreshold+abs(ks.length-len(repseq)))][0:5]
                result.append((a,i,seq,similarity))
            return result
        else:
            return []

    def df_table(self):
        dr = self.get_datareader
        result={}
        table = dr.df_table()
        roundids = {row[0]:Rounds.query.filter_by(round_name=row[0]).first().id for row in table} # get all the ids to display link.
        result.update(table=table,cluster=dr.cluster_summary(),roundids = roundids)
        return result


    def cluster_display(self,cluster):
        # get the C1 dna logo, etc.
        cluster = self.get_datareader[cluster]
        seq = [ (i.split('\t')[0], int(float(i.split('\t')[1].strip())) ) for i in cluster.format(count=1, order=1, returnraw=1)[0:100]]
        alignscore=cluster.align_score()
        totalcount = int(sum(cluster.count))
        uniquecount = len(cluster.count)
        return [totalcount, uniquecount,round(alignscore,2)],[ (SeqRound.query.filter_by(sequence_id=Sequence.query.filter_by(
                    aptamer_seq=i.replace('-','')).first().id).first(),i,j) for i,j in seq]

    def plot_logo(self,cluster):
        dr=self.get_datareader
        return dr.plot_logo(cluster,save=False,count=True)


    def plot_heatmap(self):
        dr=self.get_datareader
        if dr:
            hm,df = dr.plot_heatmap()
            return hm

class SeqRound(db.Model):
    """
    Middle man class between Sequence and Rounds.
    SeqRound.sequence => Sequence class
    SeqRound.round => Rounds class
    SeqRound.count => read of this sequence in this round.
    """
    __tablename__ = 'sequence_round'
    # __table_args__ = {'extend_existing': True}
    sequence_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('sequence.id'), primary_key=True)
    rounds_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('round.id'), primary_key=True)
    count = Column(mysql.INTEGER(unsigned=True),default=1)
    sequence = relationship("Sequence", back_populates="rounds")
    round = relationship("Rounds", back_populates="sequences")

    def __repr__(self):
        return f"Sequence <{self.id_display}>, {self.count} in {self.round.round_name}"

    @property
    def name(self):
        return f'{self.id_display}'

    @property
    def tosynthesis(self):
        return (self.sequence.note and 'to synthesis' in self.sequence.note.lower())

    def display(self):
        ks = self.sequence.knownas or ''
        if ks:
            ks = 'A.K.A. : '+ks.sequence_name
        l1= self.sequence_display
        l3=f"{ks} Count: {self.count} Ratio: {self.percentage}% in {self.round.round_name} pool."
        l2=f"Length: {len(self.sequence.aptamer_seq)} n.t."
        return l1,l2,l3

    @property
    def synthesis_status(self):
        if self.sequence.note:
            return f"{self.sequence.note} - {self.sequence.date}"
        else:
            return None

    def align(self,query):
        align = Alignment(self.sequence.aptamer_seq)
        align=align.align(query,offset=False)
        return align.format(link=True,maxlength=95).split('\n')

    @property
    def aka(self):
        ks = self.sequence.knownas or ''
        if ks:
            ks = ks.sequence_name
        return ks

    @property
    def length(self):
        return len(self.sequence.aptamer_seq)

    @property
    def FP(self):
        return self.round.FP

    @property
    def RP(self):
        return self.round.RP


    @lazyproperty
    def sequence_display(self):
        return f"{self.sequence.aptamer_seq}"

    @property
    def percentage(self):
        return round(self.count/self.round.totalread*100,2)

    def percentage_in_selection(self):
        rd = db.session.query(Rounds.id).filter(Rounds.selection_id==self.round.selection_id)
        u= SeqRound.query.filter(SeqRound.sequence_id==self.sequence_id,SeqRound.rounds_id.in_(rd)).all()
        return sorted(u,key=lambda x:x.percentage,reverse=True)

    def percentage_in_other(self):
        rd = db.session.query(Rounds.id).filter(Rounds.selection_id!=self.round.selection_id)
        u= SeqRound.query.filter(SeqRound.sequence_id==self.sequence_id,SeqRound.rounds_id.in_(rd)).all()
        return sorted(u,key=lambda x:x.percentage,reverse=True)

    @property
    def id(self):
        return (self.sequence_id,self.rounds_id)

    @property
    def id_display(self):
        return convert_id_to_string(self.id[0])

    @property
    def percentage_rank(self):
        rd = sorted([i.count for i in self.round.sequences],reverse=True)
        return rd.index(self.count)+1


    def haschildren(self):
        return True

class KnownSequence(SearchableMixin,db.Model, BaseDataModel):
    __tablename__ = 'known_sequence'
    __searchable__ = ['sequence_name', 'target', 'note']
    __searablemethod__ = ['display']
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    sequence_name = Column(mysql.VARCHAR(50),unique=True) #unique=True
    rep_seq = Column(mysql.VARCHAR(200,charset='ascii'),unique=True)
    target = Column(mysql.VARCHAR(50))
    note = Column(mysql.VARCHAR(5000))
    sequence_variants =  relationship('Sequence',backref='knownas')

    def align(self, query):
        align = Alignment(self.rep_seq)
        align = align.align(query)
        return align.format(link=True, maxlength=95).split('\n')

    @property
    def name(self):
        return self.sequence_name

    @property
    def length(self):
        return len(self.rep_seq)

    def __repr__(self):
        return f"KnownSequence <{self.sequence_name}> ID:{self.id}"

    def haschildren(self):
        f = Sequence.query.filter_by(known_sequence_id=self.id).first()
        return bool(f)

    @property
    def id_display(self):
        return self.id

    def display(self):
        l1 = "Name: {}".format(self.sequence_name)
        l2 = "Sequence: {}".format(self.rep_seq)
        l3 = 'Note: {}'.format(self.note)
        return l1,l2,l3

    def plot_structure(self):
        fs = Structure(self.rep_seq, name=self.sequence_name)
        return fs.quick_plot()


    def found_in(self):
        result = db.session.query(Selection.selection_name, Rounds.selection_id, Rounds.round_name, SeqRound.rounds_id, func.sum(SeqRound.count) /
                 Rounds.totalread).join(Sequence).join(Rounds).join(Selection).filter(Sequence.known_sequence_id == self.id).group_by(SeqRound.rounds_id).all()
        result.sort(key=lambda x:x[-1],reverse=True)
        result = [ ((a,b),(c,d),"{:.2%}".format(e)) for a,b,c,d,e in result]
        return result

class AccessLog(db.Model):
    __tablename__ = 'accesslog'
    id = Column(db.Integer, primary_key=True)
    count = Column(db.Integer)
    date = Column(DateTime(), default=datetime.now)

    def add_count(self):
        self.count+=1
        self.date = datetime.now()
        n=self.id + 1 if self.id<24 else 1
        nx=AccessLog.query.get(n)
        if nx:
            nx.count=0
        else:
            db.session.add(AccessLog(id=n,count=0))

class Sequence(db.Model,BaseDataModel):
    """
    Sequence class:
    Sequence.aptamer_seq => nucleotide sequence of the sequence.
    Sequence.rounds => list of rounds instances this sequence apears in.
    """
    __tablename__ = 'sequence'
    # __table_args__ = {'extend_existing': True}
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    known_sequence_id = Column(mysql.INTEGER(unsigned=True),ForeignKey('known_sequence.id'))
    aptamer_seq = Column(mysql.VARCHAR(200,charset='ascii'),unique=True) #unique=True
    rounds = relationship("SeqRound", back_populates="sequence")
    note = Column(mysql.VARCHAR(5000))
    date = Column(DateTime())

    def align(self, query):
        align = Alignment(self.aptamer_seq)
        align = align.align(query)
        return align.format(link=True, maxlength=95).split('\n')

    @property
    def name(self):
        return self.id_display

    def __repr__(self):
        return f"Sequence ID: {self.id_display} A.K.A.: {self.knownas and self.knownas.sequence_name}"

    def haschildren(self):
        return False

    @property
    def length(self):
        return len(self.aptamer_seq)

    @property
    def id_display(self):
        return convert_id_to_string(self.id)

    @property
    def aka(self):
        if self.knownas: return self.knownas.sequence_name
        else: return self.id_display

    def similar_to(self,n=10):
        # return tuble of knownsequence,distance
        ks = KnownSequence.query.filter(KnownSequence.id!=self.known_sequence_id).all()
        ksdistance = [lev_distance(self.aptamer_seq,i.rep_seq,n+abs(i.length-self.length)) for i in ks]
        similarity = sorted([(i,j) for i,j in zip(ks,ksdistance)],key=lambda x: x[1])
        similarity = [(ks, i) for ks, i in similarity if i <=
                      (n+abs(ks.length-self.length))]
        return similarity

    def plot_structure(self):
        fs=Structure(self.aptamer_seq,name=self.id_display)
        return fs.quick_plot()

class Rounds(SearchableMixin,db.Model, BaseDataModel):
    """
    Rounds class:
    Rounds.selection_id => id of a selection this round belongs to.
    Rounds.selection => selection instance this round belongs to.
    Rounds.round_name => name of the round.
    Rounds.target => target of the round.
    Rounds.totalread => total read of the round.
    Rounds.forward_primer / Rounds.reverse_primer => primer ID of the primer for this round.
    Rounds.parent_id / Rounds.parent => ID / Instance of the current round's parent.
    Rounds.children => list of instance of current round's children.
    """
    __tablename__ = 'round'
    __searchable__ = ['round_name', 'target', 'note']
    __searablemethod__= ['display']
    # __table_args__ = {'extend_existing': True}
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    selection_id = Column(mysql.INTEGER(unsigned=True),ForeignKey('selection.id'))
    round_name = Column(String(50))
    sequences = relationship("SeqRound", back_populates="round")
    target = Column(String(50))
    totalread = Column(mysql.INTEGER(unsigned=True),default=0)
    note = Column(String(5000))
    forward_primer = Column(mysql.INTEGER(unsigned=True),
                            ForeignKey('primer.id'))
    reverse_primer = Column(mysql.INTEGER(unsigned=True),
                            ForeignKey('primer.id'))
    samples = relationship('NGSSample',backref='round')
    date = Column(DateTime(), default=datetime.now)
    parent_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('round.id'))
    children = relationship("Rounds")
    def __repr__(self):
        return f"Round <{self.round_name}>, ID:{self.id}"

    @property
    def tree_color(self):
        return 'red' if self.totalread else 'black'

    @property
    def name(self):
        return self.round_name

    @property
    def sequenced(self):
        return bool(self.samples)

    def display(self):
        selectionname = self.selection_id and Selection.query.get(self.selection_id).selection_name
        fp = self.forward_primer and Primers.query.get(self.forward_primer).name
        rp = self.reverse_primer and Primers.query.get(self.reverse_primer).name
        l1=f"{self.round_name}"

        l2=f"Target: {self.target}, Selection name: {selectionname}, Total Read: {self.totalread}"
        l3=f"Primers: {fp} + {rp}, Date:{self.date}"
        l4=f"Note: {self.note}"
        return l1,l2,l3,l4

    def _top_seq(self,n):
        return SeqRound.query.filter_by(rounds_id=self.id).order_by(SeqRound.count.desc()).limit(n).all()
        # seq = sorted(self.sequences, key=lambda x: x.count, reverse=True)
        # oldread = self.totalread
        # self.totalread = sum(i.count for i in self.sequences)
        # if oldread != self.totalread:
        #     db.session.commit()
        # return seq[0:n]

    def top_seq(self,n):
        seq = ["{}: {:.2%}".format(
            i.sequence.aka, i.count/(self.totalread)) for i in self._top_seq(n)]
        return "; ".join(seq)

    def info(self):
        # l1="Total read: {}  Unique read: {}".format(self.totalread,len(self.sequences))
        l1="Total read: {}".format(self.totalread)
        # l2="Top Seq: {}".format(self.top_seq(5))
        parent = "None" if not self.parent_id else Rounds.query.get(self.parent_id).round_name
        l3="Parent: {}".format(parent)
        children = [i.round_name for i in self.children]
        l4="Children: {}".format("None" if not children else '; '.join(children))
        return l1,l3,l4


    @property
    def unique_read(self):
        return len(self.sequences)

    @property
    def parent(self):
        return Rounds.query.get(self.parent_id or 0)

    @property
    def FP(self):
        return Primers.query.get(self.forward_primer or 0)
    @property
    def RP(self):
        return Primers.query.get(self.reverse_primer or 0)

    def haschildren(self):
        return bool(self.totalread) or bool(self.samples)

    def plot_pie(self):
        # fig, ax = Figure.subplots(figsize=(4, 4), subplot_kw=dict(aspect="equal"))
        fig = Figure(figsize=(6,4))
        ax = fig.subplots(subplot_kw=dict(aspect="equal"))
        seq = [(i.sequence.aka, i.count/(self.totalread)) for i in self._top_seq(9)]
        _seq = [i for i in seq if i[1]>=0.01]
        seq = _seq or seq[0:2]
        seq = seq + [('<{:.1%}'.format(seq[-1][1]), 1-sum([i[1] for i in seq]))]
        data = [i[1] for i in seq]
        start = sum(i for i in data[:-1] if i>0.05)
        start += 0.5*sum(i for i in data[:-1] if i<=0.05)
        wedges, texts, autotexts = ax.pie(data, wedgeprops=dict(width=0.5), autopct=lambda pct: "{:.1f}%".format(pct),
                                        textprops=dict(color="w", fontsize=6), pctdistance=0.75,startangle=180-360*start)
        kw = dict(arrowprops=dict(arrowstyle="-"),zorder=0, va="center")
        lastxy=(1,0)
        ax.set_title(self.round_name, weight='bold')
        for i, p in enumerate(wedges):
            ang = (p.theta2 - p.theta1)/2 + p.theta1
            y = np.sin(np.deg2rad(ang))
            x = np.cos(np.deg2rad(ang))
            horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
            connectionstyle = "angle,angleA=0,angleB={}".format(ang)
            kw["arrowprops"].update({"connectionstyle": connectionstyle})
            # jitter
            if np.sign(x)==lastxy[0]:
                if abs(y-lastxy[1])<0.06:
                    y += 0.06*np.sign(x)-(y-lastxy[1])
            ax.annotate(seq[i][0], xy=(x, y), xytext=(1.2*np.sign(x), 1.2*y),
                        horizontalalignment=horizontalalignment, fontsize=8, **kw)
            lastxy= (np.sign(x),y)
        fig.set_tight_layout(True)
        return fig

class Selection(SearchableMixin,db.Model, BaseDataModel):
    """
    Selection Class:
    Selection.selection_name => name of selection.
    Selection.target => target of selection.
    Selection.rounds => list of Rounds instances that belongs to this selection.
    """
    __tablename__ = 'selection'
    __searchable__=['selection_name','target','note']
    __searablemethod__ = ['display']
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    selection_name = Column(String(100),unique=True)
    target = Column(String(50))
    note = Column(String(5000))
    rounds = relationship('Rounds',backref='selection')
    date = Column(DateTime(), default=datetime.now)

    @property
    def name(self):
        return self.selection_name

    def __repr__(self):
        return f"Selection <{self.selection_name}>, ID: {self.id}"

    def json_tree_notes(self):
        sr = [i for i in self.rounds]
        for r in self.rounds:
            if r.parent and r.parent not in sr:
                sr.append(r.parent)
        result = [(i.round_name, i.note,url_for('ngs.details',table='round',id=i.id)) for i in sr]
        result.append((self.selection_name, self.note, "#"))
        return result

    def json_tree(self):
        """return tree json"""
        sr = [ i for i in self.rounds]
        for r in self.rounds:
            if r.parent and r.parent not in sr:
                sr.append(r.parent)
        result = {'name': f"ID-{self.id}", 'note': self.note,'color':'black',
                  'url': '', 'children': []}
        todel = []
        for r in sr:
            if (not r.parent) or (not (r in self.rounds)):
                result['children'].append({'name': r.round_name,'note':r.note, 'color':r.tree_color,
            'url': url_for('ngs.details', table='round', id=r.id), 'children': []})
                todel.append(r)
        for i in todel: sr.remove(i)

        while sr:
            toremove = []
            for i in sr:
                p = self.search_tree(i.parent.round_name, result)
                if p:
                    p['children'].append({'name': i.round_name, 'note': i.note, 'color': i.tree_color,
                    'url': url_for('ngs.details', table='round', id=i.id),'children':[]})
                    toremove.append(i)
            for i in toremove:

                sr.remove(i)
        return result

    def search_tree(self,ele,tree):
        def dfs(tree):
            yield tree
            for v in tree.get('children',[]):
                for u in dfs(v):
                    yield u
        for i in dfs(tree):
            if i['name'] == ele:
                return i
        return False

        # TODO why this is wrong?
        # if ele == tree['name']:
        #     return tree
        # else:
        #     for i in tree['children']:
        #         return self.search_tree(ele,i)



    def display(self):
        line1 = f"{self.selection_name}"
        line2=f"Target: {self.target}, Sequenced Rounds: {len(self.rounds)}, Date: {self.date}"
        line3= f"Note: {self.note}"
        return line1,line2,line3

    def haschildren(self):
        return bool(self.rounds)

    def info(self):
        l1=("Total Rounds",len(self.rounds))
        l2=("Sequenced",len([i for i in self.rounds if i.totalread]))
        return l1,l2

class Primers(SearchableMixin,db.Model, BaseDataModel):
    """
    Primers Class:
    Primers.name => name of the primer.
    Primers.sequence => nucleotide sequence of this primer.
    Primers.role => role of this primer, can be: PD, NGS, SELEX, Other.
    """
    __tablename__ = 'primer'
    __searchable__ = ['name', 'role', 'note']
    __searablemethod__ = ['display']
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    name = Column(String(20), unique=True)
    sequence = Column(mysql.VARCHAR(200, charset='ascii'), unique=True)
    role = Column(String(10)) # can be PD
    note = Column(String(3000))

    def __repr__(self):
        return f"Primer {self.name}, ID:{self.id}"

    def align(self, query):
        align = Alignment(self.sequence)
        align = align.align(query)
        return align.format(link=True, maxlength=95).split('\n')


    def display(self):
        l1 = f"{self.name}"
        l2 = f"{self.sequence}"
        l3 = f"Type: {self.role}, Note: {self.note}"
        return l1,l2,l3

    def haschildren(self):
        return self.role != 'Other'

    @property
    def sequence_rc(self):
        return reverse_comp(self.sequence)

def generate_sample_info(nsg_id):
    """
    sample info is a list consist of [ () ()]
    (round_id, fpindex, rpcindex, fp, rpc)
    """
    nsg = NGSSampleGroup.query.get(nsg_id)
    savefolder = current_app.config['UPLOAD_FOLDER']
    f1 = json.loads(nsg.datafile)['file1']
    f2 = json.loads(nsg.datafile)['file2']
    if f1:
        f1 = os.path.join(savefolder, f1)
    if f2:
        f2 = os.path.join(savefolder, f2)
    sampleinfo = []
    for sample in nsg.samples:
        round_id = sample.round_id
        fpindex = Primers.query.get(sample.fp_id or 1).sequence
        rpindex = Primers.query.get(sample.rp_id or 1).sequence
        rd = Rounds.query.get(round_id)
        fp = Primers.query.get(rd.forward_primer or 1).sequence
        rp = Primers.query.get(rd.reverse_primer or 1).sequence
        sampleinfo.append(
            (round_id, fpindex, reverse_comp(rpindex), fp, reverse_comp(rp)))
    return f1, f2, sampleinfo

class NGSSampleGroup(SearchableMixin, db.Model, BaseDataModel, DataStringMixin):
    __tablename__ = 'ngs_sample_group'
    __searchable__ = ['name', 'note']
    __searablemethod__ = ['display']
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    name = Column(String(500))
    note = Column(mysql.VARCHAR(5000))
    date = Column(DateTime(), default=datetime.now)
    samples = relationship(
        'NGSSample', backref='ngs_sample_group', cascade="all, delete-orphan")
    datafile = Column(String(200))
    processingresult = Column(db.Text)
    task_id = Column(db.String(36), ForeignKey('task.id', ondelete='SET NULL'),nullable=True)
    data_string = Column(mysql.TEXT, default="{}")
    commit_threshold = data_string_descriptor('commit_threshold',2)()

    commit_result = data_string_descriptor('commit_result',{})()
    temp_result = data_string_descriptor('temp_result', '')()
    temp_commit_result = data_string_descriptor('temp_commit_result', {})()

    filters = data_string_descriptor('filters',[0,1,0,30,2])() # processing filter, list, in the order of: equal-match-length; rev-comp ; Q score; Qscore threshold; count threshold

    @property
    def _filters(self):
        return self.filters or [0, 1, 0, 30, 2]

    def __repr__(self):
        return f"NGS Sample <{self.name}>, ID:{self.id}"

    def haschildren(self):
        return self.processed

    def get_commit_result(self,round_id):
        return self.commit_result.get(str(round_id),None)

    def get_temp_commit_result(self, round_id):
        return self.temp_commit_result.get(str(round_id), None)

    @property
    def showdatafiles(self):
        if self.datafile:
            data=json.loads(self.datafile)
            return '\n'.join(['File 1',data['file1'],'File 2', data['file2']])
        else:
            return None
    @property
    def files(self):
        if self.datafile:
            uf = current_app.config['UPLOAD_FOLDER'] + '/'
            r = json.loads(self.datafile)
            return uf+r.get('file1',""),uf+r.get('file2',"")
        return []


    @property
    def processed(self):
        return bool(self.processingresult) and (not self.task_id)

    @property
    def progress(self):
        if self.task_id:
            return "{:.2f}".format(Task.query.get(self.task_id).progress)
        else:
            return 100

    def display(self):
        l1=f"{self.name}  - Date: {self.date}"
        l2 = f"{len(self.samples)} Samples, Note: {self.note}"
        l3 = f"DataFile: {self.datafile}"
        l4 = f"Committed : {bool(self.processingresult)}"
        return l1,l2,l3,l4

    def launch_task(self, commit,filters):
        if commit == 'retract':
            filters = self.filters
            if not filters:
                filters = [0,1,0,30,self.commit_threshold]
        job = current_app.task_queue.enqueue(
            'app.tasks.ngs_data_processing.parse_ngs_data', self.id, commit,filters,job_timeout=3600*10)
        t = Task(id=job.get_id(),name=f"Parse NGS Sample <{self.name}> data.")
        db.session.add(t)
        db.session.commit()
        self.task_id = t.id
        db.session.commit()
        return t

    def can_start_task(self):
        return self.datafile and (not self.task_id)

    def files_validation(self):
        """validate files have same length,
        samples have correct fp index, rp index, fp and rp
        primers match as stated in label for the first 200 sequences.
        and make file1 to be forward strand, file2 to be reverse strand.
        """
        f1,f2,sampleinfo = generate_sample_info(self.id)
        self._check_equal_file_length(f1,f2)
        self._check_primers_match(f1,f2,sampleinfo)

    def _check_equal_file_length(self,f1,f2):
        """
        don't check if there is no file2.
        """
        if f2:
            with self.reader_obj(f1) as f, self.reader_obj(f2) as r:
                fb1 = file_blocks(f)
                fb2 = file_blocks(r)
                f1_break = '\n' # if f1.endswith('.fastq') else b'\n'
                f2_break = '\n' # if f2.endswith('.fastq') else b'\n'
                fb1length = sum(bl.count(f1_break) for bl in fb1)
                fb2length = sum(bl.count(f2_break) for bl in fb2)
            assert fb1length==fb2length, ("Files are not of the same length.")

    def reader_obj(self, filename):
        if filename.endswith('.fastq'):
            return open(filename, 'rt')
        elif filename.endswith('.gz'):
            return gzip.open(filename, 'rt')
        else:
            return None

    def read_lines(self,filename,n=2000):
        """
        determine file type is fastq or gz, then return n lines read into file.
        """
        lines=[]
        f = self.reader_obj(filename)
        if f:
            with f:
                for line in islice(f, 1, n, 4):
                    lines.append(line.strip())
        return lines

    def _check_primers_match(self,f1,f2,sampleinfo):
        forward ,reverse = [],[]
        needtoswap = 0
        match = 0
        revcomp=0
        forward = self.read_lines(f1)
        if f2:
            reverse = self.read_lines(f2)
        for idx,_f in enumerate(forward):
            if reverse:
                _r = reverse[idx]
                _f_mid =max(len(_f)//2,10)
                mid20 = _f[_f_mid-10:_f_mid+10]
                if reverse_comp(mid20) in _r:#_f==reverse_comp(_r):
                    revcomp+=1
                else:
                    revcomp-=1
            else:
                _r = reverse_comp(_f)

            findmatch = -1
            if needtoswap > 0:
                totest, totest_r, vote = _r, _f, 1
            else:
                totest, totest_r,vote = _f,_r,-1
            for _, *primers in sampleinfo:
                if all([i in totest for i in primers]):
                    needtoswap += vote
                    findmatch = 1
                    break
                elif all([i in totest_r for i in primers]):
                    needtoswap -= vote
                    findmatch = 1
                    break
                else:
                    continue
            match += findmatch
        # assert revcomp>=0,('Too Many non reverse-complimentary sequences.')
        # assert match >=0, ('Too many index primers and slection primers don\'t match.')
        if needtoswap>0:
            datadict=json.loads(self.datafile)
            datadict['file1'],datadict['file2']=datadict['file2'],datadict['file1']
            self.datafile = json.dumps(datadict, separators=(',', ':'))
            db.session.commit()

class NGSSample(db.Model,BaseDataModel):
    __tablename__='ngs_sample'
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    round_id = Column(mysql.INTEGER(unsigned=True),ForeignKey('round.id'))
    fp_id =  Column(mysql.INTEGER(unsigned=True),ForeignKey('primer.id'))
    rp_id = Column(mysql.INTEGER(unsigned=True),ForeignKey('primer.id'))
    sample_group_id = Column(mysql.INTEGER(unsigned=True),ForeignKey('ngs_sample_group.id'))

    def __repr__(self):
        return f"ID:{self.id},Round:{self.round_id}"

    def info(self):
        """ return information in the order of
        round name, round FP, round RP, index FP, index RP"""
        rd  = self.round
        fp = Primers.query.get(rd.forward_primer or 0)
        rp = Primers.query.get(rd.reverse_primer or 0)
        fpi = Primers.query.get(self.fp_id )
        rpi = Primers.query.get(self.rp_id )
        return [(rd.round_name, rd.__tablename__, rd.id)] + [(p.name, p.__tablename__,p.id) if p else (None,None,None)for p in (fp,rp,fpi,rpi)]

class Task(db.Model,BaseDataModel):
    __tablename__='task'
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    progress = db.Column(db.Float,default=0)
    complete = db.Column(db.Boolean, default=False)
    date = Column(DateTime(), default=datetime.now)
    ngssample = relationship(
        'NGSSampleGroup', backref=db.backref('task', passive_deletes=True))

    def __repr__(self):
        return f"Task:{self.name}, ID:{self.id}"

class Slide(SearchableMixin,db.Model):
    __tablename__='slide'
    __searchable__=['title','body','tag','note','ppt_id','flag','author']
    __searablemethod__ = []
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    title = Column(mysql.TEXT)
    body = Column(mysql.TEXT)
    ppt_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('powerpoint.id'))
    note = Column(String(5000))
    tag = Column(String(900))
    author = Column(String(100))
    page = Column(mysql.INTEGER(unsigned=True))
    date = Column(DateTime(), default=datetime.now)
    _flag = Column(String(10))

    def __repr__(self):
        return f"<Slide {self.id}>"

    @property
    def flag(self):
        return self._flag if self._flag else ""

    @property
    def uri(self):
        return self.ppt.path + f'/Slide{self.page}.PNG'

    @staticmethod
    def tags_list(n=20,returncount=False):
        tags = db.session.query(Slide.tag).filter(Slide.tag!=None).all()
        c = Counter([j.strip() for i in tags for j in i[0].split(',') if j.strip()])
        c = c.most_common(n)
        if returncount:
            return c
        else:
            return [i[0] for i in c]
    
    @staticmethod
    def authors_list():
        slides = Slide.query.all()
        counter = {}
        for slide in slides:
            if slide.author in counter:
                counter[slide.author][0] += 1
                counter[slide.author][1] += (slide.date.date() >= datetime.now().date())
            else:
                counter[slide.author] = [
                    1, int(slide.date.date() >= datetime.now().date())]
        anonymous = counter.pop(None,None)
        if anonymous:
            counter['Anonymous']=anonymous
        return sorted([(k,i[0],i[1]) for k,i in counter.items()],key = lambda x:x[:-3:-1],reverse=True)



    @classmethod
    def search_in_id(cls, query, fields, ids, date_from, date_to, page, per_page):
        """
        string, ['all', 'title', 'body'], ['15', '16']
        """
        if not query.strip():
            if 'all' in ids:
                entries = cls.query.filter(cls.date.between(date_from,date_to)).order_by(
                    cls.date.desc()).paginate(page, per_page, False)
            else:
                ids = [int(i) for i in ids]
                entries = cls.query.filter(cls.ppt_id.in_(ids), cls.date.between(date_from, date_to)).order_by(
                    cls.date.desc()).paginate(page, per_page, False)
            return entries.items, entries.total  # just return matching id slides

        if not current_app.elasticsearch:
            return [], 0
        if 'all' in fields:
            fields = ['title', 'body', 'tag', 'note',]
        base = {'multi_match': {'query': query, 'fields': fields}}
        if 'all' not in ids:
            ids = [int(i) for i in ids]
            base = {'bool': {'must': [base], 'filter':{"terms": {"ppt_id":ids}}}}
        result = current_app.elasticsearch.search(\
            index='slide', body={'query': base, 'from': (page - 1) * per_page,'size':per_page})

        ids = [int(hit['_id']) for hit in result['hits']['hits']]
        total = result['hits']['total']
        # to account for difference between elastic search version on mac and ubuntu.
        if isinstance(total, dict):
            total = total['value']
        if total==0:
            return cls.query.filter_by(id=0),0
        when = [ (k,i) for i,k in enumerate(ids) ]
        return cls.query.filter(cls.id.in_(ids), cls.date.between(date_from, date_to)).order_by(db.case(when, value=cls.id)), total

class PPT(db.Model):
    __tablename__ = 'powerpoint'
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    name = Column(String(200))
    note = Column(String(5000))
    project_id = Column(mysql.INTEGER(unsigned=True),ForeignKey('project.id'))
    path = Column(String(500),unique=True)
    md5 = Column(String(200),unique=True)
    revision = Column(db.Integer)
    slides = relationship('Slide', backref='ppt', cascade="all, delete-orphan")
    date = Column(DateTime(), default=datetime.now)
    def __repr__(self):
        return f"<PPT {self.id}>"

    @property
    def uri(self):
        self.slides.sort(key=lambda x: (x.date,x.page), reverse=True)
        if self.slides:
            return self.slides[0].uri
        else:
            return 'FolderEmpty.png'

class Project(db.Model):
    __tablename__ = 'project'
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    name = Column(String(200),unique=True)
    note = Column(String(2000))
    ppts = relationship('PPT', backref='project')
    date = Column(DateTime(), default=datetime.now)

    def __repr__(self):
        return f"<Project {self.id}>"

    @property
    def uri(self):
        # self.ppts.sort(key=lambda x: x.date, reverse=True)
        if self.ppts:
            self.ppts.sort(key=lambda x: x.date,)
            return self.ppts[-1].uri
        else:
            return 'FolderEmpty.png'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))


models_table_name_dictionary = {'user':User,'task': Task, 'ngs_sample': NGSSample,
'ngs_sample_group':NGSSampleGroup, 'primer':Primers, 'selection':Selection, 'round':Rounds, 'sequence':Sequence,
'known_sequence':KnownSequence, 'sequence_round':SeqRound,'analysis':Analysis,'project':Project,'ppt':PPT,'slide':Slide}
# from app.tasks.ngs_data_processing import
from app.utils.ngs_util import reverse_comp,file_blocks,create_folder_if_not_exist
from app.utils.analysis import DataReader,Alignment,datareader_API_dict
