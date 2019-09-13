

from datetime import datetime
from sqlalchemy import Column, String,ForeignKey,DateTime
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Table,MetaData
import time

import sqlalchemy
sqlalchemy.__version__

engine= create_engine('mysql+pymysql://root:password@localhost/ngs')
# engine.execute("CREATE DATABASE ngs")

Base = declarative_base()

Session = sessionmaker(bind=engine)

session = Session()

# engine.table_names()
#
#
# meta = MetaData()
#
# meta.bind=engine
#
# meta.reflect(extend_existing=True)

def auto_rollback(func):
    def wrapper(*args,**kwargs):
        try:
            r=func(*args,**kwargs)
            return r
        except Exception as e:
            session.rollback()
            print(e)
            return None
    return wrapper


class SeqRound(Base):
    __tablename__ = 'sequence_round'
    # __table_args__ = {'extend_existing': True}
    sequence_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('sequence.id'), primary_key=True)
    rounds_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('rounds.id'), primary_key=True)
    count = Column(mysql.INTEGER(unsigned=True))
    sequence = relationship("Sequence", back_populates="rounds")
    round = relationship("Rounds", back_populates="sequences")

    def __repr__(self):
        return f"SeqRound :{self.count} Seq{self.sequence_id} in {self.round.round_name}"

class KnownSequence(Base):
    __tablename__ = 'known_sequence'
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    sequence_name = Column(mysql.VARCHAR(50),unique=True) #unique=True
    rep_seq = Column(mysql.VARCHAR(200,charset='ascii'))
    note = Column(mysql.VARCHAR(500))
    sequence_variants =  relationship('Sequence',backref='knownas')

    def __repr__(self):
        return f"KnownSequence id:{self.id}, Sequence Name: {self.sequence_name}"

class Sequence(Base):
    __tablename__ = 'sequence'
    # __table_args__ = {'extend_existing': True}
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    known_sequence_id = Column(mysql.INTEGER(unsigned=True),ForeignKey('known_sequence.id'))
    aptamer_seq = Column(mysql.VARCHAR(200,charset='ascii'),unique=True) #unique=True
    rounds = relationship("SeqRound", back_populates="sequence")

    def __repr__(self):
        return f"Sequence id:{self.id},sequence:{self.aptamer_seq}"

class Rounds(Base):
    __tablename__ = 'rounds'
    # __table_args__ = {'extend_existing': True}
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    selection_id = Column(mysql.INTEGER(unsigned=True),ForeignKey('selection.id'))
    round_name = Column(String(50))
    sequences = relationship("SeqRound", back_populates="round")
    target = Column(String(50))
    totalread = Column(mysql.INTEGER(unsigned=True))
    note = Column(String(300))
    primerset = Column(String(20))
    date = Column(DateTime(), default=datetime.utcnow)
    def __repr__(self):
        return f"Round id:{self.id},name:{self.round_name}"

class Selection(Base):
    __tablename__ = 'selection'
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    selection_name = Column(String(100),unique=True)
    target = Column(String(50))
    note = Column(String(300))
    rounds = relationship('Rounds',backref='selection')

    def __repr__(self):
        return f"Selection id:{self.id}, selection name:{self.selection_name}"

Base.metadata.create_all(engine)


@auto_rollback
def create_selection(selection_name,target,note):
    selection=session.query(Selection).filter_by(selection_name=selection_name).first()
    if selection:
        print('selection <{}> already exist.'.format(selection.selection_name))
        return selection
    selection = Selection(selection_name=selection_name,target=target,note=note)
    session.add(selection)
    session.commit()
    return selection

@auto_rollback
def create_round(roundname,totalread,target,primerset,note,selection):
    round=session.query(Rounds).filter_by(round_name=roundname,selection_id=selection.id).first()
    if round:
        print('round <{}> already exist in selection <{}>.'.format(round.round_name,selection.selection_name))
        return round
    roundtoadd = Rounds(round_name=roundname,totalread=totalread,
                    primerset=primerset,target=target,note=note,selection=selection)
    session.add(roundtoadd)
    session.commit()
    return roundtoadd

@auto_rollback
def create_association(sequences,round,count):
    tosave = [SeqRound(sequence_id=i.id,rounds_id=round.id,count=c) for i,c in zip(sequences,count)]
    session.bulk_save_objects(tosave)
    session.commit()

@auto_rollback
def create_sequence(round,sequencelist,count):
    """
    use temp table to create a list of sequence objects.
    """
    countdict = dict(zip(sequencelist,count))
    temp = Table('temp',Base.metadata,
                Column('seq',mysql.VARCHAR(200,charset='ascii'),primary_key=True),extend_existing=True)
    Base.metadata.create_all(engine)
    session.execute(temp.insert(),[{'seq':i} for i in sequencelist])
    session.commit()
    already_exist=session.query(Sequence).join(temp,temp.c.seq==Sequence.aptamer_seq).all()
    count = [countdict[i.aptamer_seq] for i in already_exist]
    session.commit()
    temp.drop(engine)
    # already_exist_seqround = [SeqRound(sequence_id=i.id,rounds_id=round.id,count=countdict[i.aptamer_seq]) for i in already_exist]
    if count:
        create_association(already_exist,round,count)
    new = set(sequencelist) - set([i.aptamer_seq for i in already_exist])
    new = [Sequence(aptamer_seq=i) for i in new]
    if new:
        session.add_all(new)
        session.commit()
        count = [countdict[i.aptamer_seq] for i in new]
        create_association(new,round,count)
    return None

@auto_rollback
def create_knownsequence(sequence_name, rep_seq, note,):
    new = KnownSequence(sequence_name=sequence_name,rep_seq=rep_seq,note=note)
    session.add(new)
    session.commit()
    return new



def list_old_table_round_name(oldtablename):
    old = Table(oldtablename,Base.metadata,autoload=True,autoload_with=engine)
    oldentry = session.query(old).first()
    result = [i for i in oldentry.keys() if (i not in ['id','aptamer_seq']) and (not i.endswith('_per'))]
    return result

list_old_table_round_name('20190701_vegf_table_percentage')


def convert_old_style_to_new(oldtablename,selection_name,roundlist,target,note,primerset,threshold=1,):
    selection = create_selection(selection_name,target,note)
    olddata =  Table(oldtablename,Base.metadata,autoload=True,autoload_with=engine)
    for r in roundlist:
        roundata=session.query(olddata.c.aptamer_seq,getattr(olddata.c,r)).filter(getattr(olddata.c,r)>=threshold).all()
        sequencelist =[i[0] for i in roundata]
        count = [i[1] for i in roundata]
        round_ = create_round(r,sum(),target,primerset,note,selection)
        create_sequence(round_,)


a=["SOMAFP	    ", "CGCCCTCGTCCCATCTC",
"SOMARP	    ", "CGTTCTCGGTTGGTGTTC",
"PatsFP	    ", "ACATGGAACAGTCGAGAATCT",
"PatsRP	    ", "ATGAGTCTGTTGTTGCTCA",
"N2FP	    ", "TCTGACTAGCGCTCTTCA",
"LadderRP	", "CGACTCGACTAAACAGCAC",
"LadderRPC	", "GTGCTGTTTAGTCGAGTCG",
"IronmanTFP	", "GATGTGAGTGTGTGACGATG",
"IronmanRP	", "GGTCTTGTTTCTTCTCTGTG",
"IronmanRPC	", "CACAGAGAAGAAACAAGACC",
"VEGF33RP1C	", "GAGATCCGACTCACTGG"]

a = [i.strip() for i in a]

from itertools import izip
c = [ (a[i*2],a[i*2+1]) for i in range(len(a)//2)]
c
