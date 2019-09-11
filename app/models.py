from app import db,login
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from hashlib import md5
from time import time
import jwt
from flask import current_app
from itertools import islice
import json
from sqlalchemy import Column, String,ForeignKey,DateTime
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import relationship
from app.utils.ngs_util import convert_id_to_string



class User(UserMixin,db.Model):
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email= db.Column(db.String(120), index=True, unique=True)
    privilege = db.Column(db.String(10),default='user')
    password_hash = db.Column(db.String(128))

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
        def testfunction(n):
            for i in range(n):
                print("****runging test -", i)
        job=current_app.task_queue.enqueue(testfunction,n)
        


class BaseDataModel():
    @property
    def id_display(self):
        return self.id



class SeqRound(db.Model):
    __tablename__ = 'sequence_round'
    # __table_args__ = {'extend_existing': True}
    sequence_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('sequence.id'), primary_key=True)
    rounds_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('round.id'), primary_key=True)
    count = Column(mysql.INTEGER(unsigned=True))
    sequence = relationship("Sequence", back_populates="rounds")
    round = relationship("Rounds", back_populates="sequences")

    def __repr__(self):
        return f"SeqRound :{self.count} Seq{self.sequence_id} in {self.round.round_name}"

    def display(self):
        rd = Rounds.query.get(self.rounds_id)
        sq = Sequence.query.get(self.sequence_id)
        ks = sq.knownas or ''
        if ks:
            ks = 'Known As: '+ks.sequence_name+'\n'
        l1= f"5'- {sq.aptamer_seq} -3'"
        l2=f"{ks}Count: {self.count} Ratio: {round(self.count/rd.totalread*100,2)}% in {rd.round_name} pool."
        return [l1,l2]

    @property
    def id(self):
        return self.sequence_id

    @property
    def id_display(self):
        return convert_id_to_string(self.id)

    def haschildren(self):
        return True

class KnownSequence(db.Model,BaseDataModel):
    __tablename__ = 'known_sequence'
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    sequence_name = Column(mysql.VARCHAR(50),unique=True) #unique=True
    rep_seq = Column(mysql.VARCHAR(200,charset='ascii'))
    note = Column(mysql.VARCHAR(500))
    sequence_variants =  relationship('Sequence',backref='knownas')

    def __repr__(self):
        return f"KnownSequence id:{self.id}, Sequence Name: {self.sequence_name}"

class Sequence(db.Model,BaseDataModel):
    __tablename__ = 'sequence'
    # __table_args__ = {'extend_existing': True}
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    known_sequence_id = Column(mysql.INTEGER(unsigned=True),ForeignKey('known_sequence.id'))
    aptamer_seq = Column(mysql.VARCHAR(200,charset='ascii'),unique=True) #unique=True
    rounds = relationship("SeqRound", back_populates="sequence")

    def __repr__(self):
        return f"Sequence id:{self.id},sequence:{self.aptamer_seq}"

    def haschildren(self):
        return False

    @property
    def id_display(self):
        return convert_id_to_string(self.id)




class Rounds(db.Model,BaseDataModel):
    __tablename__ = 'round'
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
    def __repr__(self):
        return f"Round id:{self.id},name:{self.round_name}"

    def display(self):
        selectionname = self.selection_id and Selection.query.get(self.selection_id).selection_name
        fp = self.forward_primer and Primers.query.get(self.forward_primer).name
        rp = self.reverse_primer and Primers.query.get(self.reverse_primer).name
        l1=f"{self.round_name}"

        l2=f"Target: {self.target}, Selection name: {selectionname}, Total Read: {self.totalread}"
        l3=f"Primers: {fp} + {rp}, Date:{self.date}"
        l4=f"Note: {self.note}"
        return l1,l2,l3,l4

    @property
    def unique_read(self):
        return len(self.sequences)

    def haschildren(self):
        return bool(self.totalread) or bool(self.samples)


class Selection(db.Model,BaseDataModel):
    __tablename__ = 'selection'
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    selection_name = Column(String(100),unique=True)
    target = Column(String(50))
    note = Column(String(300))
    rounds = relationship('Rounds',backref='selection')
    date = Column(DateTime(), default=datetime.now)
    # samples = relationship('NGSSample',backref='selection')

    def __repr__(self):
        return f"Selection id:{self.id}, selection name:{self.selection_name}"

    def display(self):
        line1 = f"{self.selection_name}"
        line2=f"Target: {self.target}, Sequenced Rounds: {len(self.rounds)}, Date: {self.date}"
        line3= f"Note: {self.note}"
        return line1,line2,line3

    def haschildren(self):
        return bool(self.rounds)



class Primers(db.Model,BaseDataModel):
    __tablename__ = 'primer'
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    name = Column(String(20), unique=True)
    sequence = Column(mysql.VARCHAR(200, charset='ascii'), unique=True)
    role = Column(String(10)) # can be PD
    note = Column(String(300))

    def __repr__(self):
        return f"Primer {self.name}, id:{self.id}"

    def display(self):
        l1 = f"{self.name}"
        l2 = f"{self.sequence}"
        l3 = f"Type: {self.role}, Note: {self.note}"
        return l1,l2,l3

    def haschildren(self):
        return self.role != 'Other'



class NGSSampleGroup(db.Model,BaseDataModel):
    __tablename__ = 'ngs_sample_group'
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    name = Column(String(50))
    note = Column(mysql.VARCHAR(500))
    date = Column(DateTime(), default=datetime.now)
    samples = relationship('NGSSample',backref='ngs_sample_group')
    datafile = Column(String(200))
    processingresult = Column(db.Text)
    task_id = Column(db.String(36),ForeignKey('task.id'))

    def __repr__(self):
        return f"NGSSampleGroup: {self.name}, {len(self.samples)} samples"

    def haschildren(self):
        return bool(self.datafile)

    @property
    def processed(self):
        return bool(self.processingresult)

    @property
    def progress(self):
        if self.task_id:
            return "{:.2f}".format(Task.query.get(self.task_id).progress)
        else:
            return 0

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
        print("***",revcomp,match,needtoswap)
        assert revcomp>0,('Too Many non reverse-complimentary sequences.')
        assert match > 0, ('Too many index primers and slection primers don\'t match.')
        if needtoswap>0:
            print(needtoswap)
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

class Task(db.Model,BaseDataModel):
    __tablename__='task'
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    progress = db.Column(db.Float,default=0)
    complete = db.Column(db.Boolean, default=False)
    date = Column(DateTime(), default=datetime.now)

    def __repr__(self):
        return f"Task:{self.name}, ID:{self.id}"



@login.user_loader
def load_user(id):
    return User.query.get(int(id))



from app.tasks.ngs_data_processing import generate_sample_info
from app.utils.ngs_util import reverse_comp,file_blocks
