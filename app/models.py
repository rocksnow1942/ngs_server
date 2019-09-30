import numpy as np
from matplotlib.figure import Figure
from app import db,login
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, current_user
from hashlib import md5
from time import time
import jwt
from flask import current_app
from itertools import islice
import json
from sqlalchemy import Column, String,ForeignKey,DateTime,func
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import relationship
from app.utils.ngs_util import convert_id_to_string,lev_distance,reverse_comp
from app.utils.folding._structurepredict import Structure
from app.utils.ngs_util import lazyproperty
from app.utils.analysis import DataReader
from app.utils.search import add_to_index, remove_from_index, query_index

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
        self.data_string = json.dumps(self.data)

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
        print('***added',session._changes)
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
    data_string = Column(db.Text,default="{}")
    analysis_cart= data_string_descriptor('analysis_cart')()
    analysis = relationship('Analysis',backref='user')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self,password):
        self.password_hash=generate_password_hash(password)

    def check_password(self,password):
        return check_password_hash(self.password_hash,password)

    def avatar(self,size):
        digest=md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

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
        job=current_app.task_queue.enqueue("app.tasks.ngs_data_processing.test_worker",n)
    
    @property
    def isadmin(self):
        return self.privilege=='admin'

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
    note = Column(String(500))
    _rounds = data_string_descriptor('rounds')()
    analysis_file = data_string_descriptor('analysis_file','')()
    task_id = data_string_descriptor('task_id', '')()
    hist = data_string_descriptor('hist',)()
    cluster_para=data_string_descriptor('cluster_para')()
    heatmap=data_string_descriptor('heatmap','')()
    # Order: name, name_link, Seq Iddisplay, Seq Id link, (display,s.id, )
    cluster_table = data_string_descriptor('cluster_table', [])()

    def __repr__(self):
        return f"{self.name}, ID {self.id}"

    def haschildren(self):
        return (current_user.id!=self.user_id)

    @property
    def analysis_file_link(self):
        parent = current_app.config['ANALYSIS_FOLDER']
        return self.analysis_file.replace(parent,'')[1:]

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
    
    @lazyproperty
    def get_datareader(self):
        if self.analysis_file:
            return DataReader.load_json(self.analysis_file)
            
    def load_rounds(self):
        job = current_app.task_queue.enqueue('app.tasks.ngs_data_processing.load_rounds',self.id)
        t = Task(id=job.get_id(),name=f"Load analysis {self}.")
        self.task_id=t.id 
        self.save_data()
        db.session.add(t)
        db.session.commit()
        return t
    
    def build_cluster(self):
        job = current_app.task_queue.enqueue(
            'app.tasks.ngs_data_processing.build_cluster', self.id,job_timeout=3600*10)
        t = Task(id=job.get_id(), name=f"Build luster {self}.")
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
        return bool(self.cluster_para)

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
        result.update(table=dr.df_table(),cluster=dr.cluster_summary())
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
        return dr.plot_logo(cluster)

    

    def plot_heatmap(self):
        dr=self.get_datareader
        if dr:
            hm,df = dr.plot_heatmap()
            return hm


class SeqRound(db.Model):
    __tablename__ = 'sequence_round'
    # __table_args__ = {'extend_existing': True}
    sequence_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('sequence.id'), primary_key=True)
    rounds_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('round.id'), primary_key=True)
    count = Column(mysql.INTEGER(unsigned=True),default=1)
    sequence = relationship("Sequence", back_populates="rounds")
    round = relationship("Rounds", back_populates="sequences")

    def __repr__(self):
        return f"Sequence <{self.id_display}>, {self.count} in {self.round.round_name}"

    def display(self):
        ks = self.sequence.knownas or ''
        if ks:
            ks = 'A.K.A. : '+ks.sequence_name+'\n'
        l1= self.sequence_display
        l2=f"{ks}Count: {self.count} Ratio: {self.percentage}% in {self.round.round_name} pool."
        l3=f"Length: {len(self.sequence.aptamer_seq)} n.t."
        return l1,l2,l3
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

    
    @property
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
    note = Column(mysql.VARCHAR(500))
    sequence_variants =  relationship('Sequence',backref='knownas')

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



class Sequence(db.Model,BaseDataModel):
    __tablename__ = 'sequence'
    # __table_args__ = {'extend_existing': True}
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    known_sequence_id = Column(mysql.INTEGER(unsigned=True),ForeignKey('known_sequence.id'))
    aptamer_seq = Column(mysql.VARCHAR(200,charset='ascii'),unique=True) #unique=True
    rounds = relationship("SeqRound", back_populates="sequence")

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
    note = Column(String(300))
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
        seq = sorted(self.sequences, key=lambda x: x.count, reverse=True)
        oldread = self.totalread
        self.totalread = sum(i.count for i in self.sequences)
        if oldread != self.totalread:
            db.session.commit()
        return seq[0:n]
    
    def top_seq(self,n):
        seq = ["{}: {:.2%}".format(
            i.sequence.aka, i.count/(self.totalread)) for i in self._top_seq(n)]
        return "; ".join(seq)
    
    def info(self):
        l1="Total read: {}  Unique read: {}".format(self.totalread,len(self.sequences))
        l2="Top Seq: {}".format(self.top_seq(5))
        parent = "None" if not self.parent_id else Rounds.query.get(self.parent_id).round_name
        l3="Parent: {}".format(parent)
        children = [i.round_name for i in self.children]
        l4="Children: {}".format("None" if not children else '; '.join(children))
        return l1,l2,l3,l4


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
        seq = [i for i in seq if i[1]>=0.01]
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
    __tablename__ = 'selection'
    __searchable__=['selection_name','target','note']
    __searablemethod__ = ['display']
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    selection_name = Column(String(100),unique=True)
    target = Column(String(50))
    note = Column(String(300))
    rounds = relationship('Rounds',backref='selection')
    date = Column(DateTime(), default=datetime.now)
    
    @property
    def name(self):
        return self.selection_name

    def __repr__(self):
        return f"Selection <{self.selection_name}>, ID: {self.id}"

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
    __tablename__ = 'primer'
    __searchable__ = ['name', 'role', 'note']
    __searablemethod__ = ['display']
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    name = Column(String(20), unique=True)
    sequence = Column(mysql.VARCHAR(200, charset='ascii'), unique=True)
    role = Column(String(10)) # can be PD
    note = Column(String(300))
   
    def __repr__(self):
        return f"Primer {self.name}, ID:{self.id}"

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

class NGSSampleGroup(SearchableMixin, db.Model, BaseDataModel):
    __tablename__ = 'ngs_sample_group'
    __searchable__ = ['name', 'note']
    __searablemethod__ = ['display']
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    name = Column(String(50))
    note = Column(mysql.VARCHAR(500))
    date = Column(DateTime(), default=datetime.now)
    samples = relationship(
        'NGSSample', backref='ngs_sample_group', cascade="all, delete-orphan")
    datafile = Column(String(200))
    processingresult = Column(db.Text)
    task_id = Column(db.String(36),ForeignKey('task.id'))

    def __repr__(self):
        return f"NGS Sample <{self.name}>, ID:{self.id}"

    def haschildren(self):
        return bool(self.datafile)
    
    @property
    def showdatafiles(self):
        if self.datafile:
            data=json.loads(self.datafile)
            return '\n'.join(['File 1',data['file1'],'File 2', data['file2']])
        else:
            return None

    @property
    def processed(self):
        return bool(self.processingresult)

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
        l4 = f"Processed : {bool(self.processingresult)}"
        return l1,l2,l3,l4

    def launch_task(self):
        job=current_app.task_queue.enqueue('app.tasks.ngs_data_processing.parse_ngs_data',self.id)
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
        with open(f1,'rt') as f, open(f2,'rt') as r:
            fb1 = file_blocks(f)
            fb2 = file_blocks(r)
            fb1length = sum(bl.count("\n") for bl in fb1)
            fb2length = sum(bl.count("\n") for bl in fb2)
        assert fb1length==fb2length, ("Files are not of the same length.")

    def _check_primers_match(self,f1,f2,sampleinfo):
        forward ,reverse = [],[]
        needtoswap = 0
        match = 0
        revcomp=0
        with open(f1,'rt') as f, open(f2,'rt') as r:
            for line in islice(f,1,2000,4):
                forward.append(line.strip())
            for line in islice(r,1,2000,4):
                reverse.append(line.strip())
        for _f,_r in zip(forward,reverse):
            if _f==reverse_comp(_r):
                revcomp+=1
                findmatch = -1
                if needtoswap > 0:
                    totest,totest_r,vote = _r,_f,1
                else:
                    totest,totest_r,vote = _f,_r,-1
                for _,*primers in sampleinfo:
                    if all([i in totest for i in primers]):
                        needtoswap+=vote
                        findmatch = 1
                        break
                    elif all([i in totest_r for i in primers]):
                        needtoswap-=vote
                        findmatch = 1
                        break
                    else:
                        continue
                match += findmatch
            else:
                revcomp-=1
       
        assert revcomp>0,('Too Many non reverse-complimentary sequences.')
        assert match > 0, ('Too many index primers and slection primers don\'t match.')
        if needtoswap>0:
            
            datadict=json.loads(self.datafile)
            datadict['file1'],datadict['file2']=datadict['file2'],datadict['file1']
            self.datafile = json.dumps(datadict)
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

    def __repr__(self):
        return f"Task:{self.name}, ID:{self.id}"

# class Slide(SearchableMixin,db.Model):
#     __tablename__='slide'
#     __searchable__=['title','body']
    

# class Project(SearchableMixin,db.Model):
#     __tablename__ = 'project'
#     __searchable__ = ['name', 'note']
#     __searablemethod__ = []
#     id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
#     selection_id = Column(mysql.INTEGER(unsigned=True),
#                           ForeignKey('selection.id'))
#     round_name = Column(String(50))
#     sequences = relationship("SeqRound", back_populates="round")
#     target = Column(String(50))
#     totalread = Column(mysql.INTEGER(unsigned=True), default=0)
#     note = Column(String(300))
#     forward_primer = Column(mysql.INTEGER(unsigned=True),
#                             ForeignKey('primer.id'))
#     reverse_primer = Column(mysql.INTEGER(unsigned=True),
#                             ForeignKey('primer.id'))
#     samples = relationship('NGSSample', backref='round')
#     date = Column(DateTime(), default=datetime.now)
#     parent_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('round.id'))
#     children = relationship("Rounds")






@login.user_loader
def load_user(id):
    return User.query.get(int(id))


models_table_name_dictionary = {'user':User,'task': Task, 'ngs_sample': NGSSample, 
'ngs_sample_group':NGSSampleGroup, 'primer':Primers, 'selection':Selection, 'round':Rounds, 'sequence':Sequence,
'known_sequence':KnownSequence, 'sequence_round':SeqRound,'analysis':Analysis}
from app.tasks.ngs_data_processing import generate_sample_info
from app.utils.ngs_util import reverse_comp,file_blocks
