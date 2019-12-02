import numpy as np
from matplotlib.figure import Figure
from datetime import datetime
from sqlalchemy import Column, String,ForeignKey,DateTime,func
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

"""
enables interact with core NGS models in server data base.
to conncect to a spoecific server, change Config settings.
provide better naming than original system.
"""

class Config():
    SQLALCHEMY_DATABASE_URI="mysql+pymysql://hui:kanghui@192.168.86.200:3306/ngs_server?charset=utf8mb4"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy()
db.init_app(app)
app.app_context().push()

class BaseDataModel():
    @property
    def id_display(self):
        return self.id

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

class KnownSequence(db.Model, BaseDataModel):
    __tablename__ = 'known_sequence'
    __searchable__ = ['sequence_name', 'target', 'note']
    __searablemethod__ = ['display']
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    sequence_name = Column(mysql.VARCHAR(50),unique=True) #unique=True
    rep_seq = Column(mysql.VARCHAR(200,charset='ascii'),unique=True)
    target = Column(mysql.VARCHAR(50))
    note = Column(mysql.VARCHAR(5000))
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
    note = Column(mysql.VARCHAR(5000))
    date = Column(DateTime())

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


class Rounds(db.Model, BaseDataModel):
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

class Selection(db.Model, BaseDataModel):
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
        result = [(i.round_name, i.note,) for i in sr]
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
             'children': []})
                todel.append(r)
        for i in todel: sr.remove(i)

        while sr:
            toremove = []
            for i in sr:
                p = self.search_tree(i.parent.round_name, result)
                if p:
                    p['children'].append({'name': i.round_name, 'note': i.note, 'color': i.tree_color,
                    'children':[]})
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

class Primers(db.Model, BaseDataModel):
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


class NGSSampleGroup( db.Model, BaseDataModel, ):
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
    task_id = Column(db.String(36), ForeignKey(
        'task.id', ondelete='SET NULL'), nullable=True)
    data_string = Column(mysql.TEXT, default="{}")



    def __repr__(self):
        return f"NGS Sample <{self.name}>, ID:{self.id}"

    def haschildren(self):
        return self.processed



class NGSSample(db.Model, BaseDataModel):
    __tablename__ = 'ngs_sample'
    id = Column(mysql.INTEGER(unsigned=True), primary_key=True)
    round_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('round.id'))
    fp_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('primer.id'))
    rp_id = Column(mysql.INTEGER(unsigned=True), ForeignKey('primer.id'))
    sample_group_id = Column(mysql.INTEGER(
        unsigned=True), ForeignKey('ngs_sample_group.id'))

    def __repr__(self):
        return f"ID:{self.id},Round:{self.round_id}"

    def info(self):
        """ return information in the order of
        round name, round FP, round RP, index FP, index RP"""
        rd = self.round
        fp = Primers.query.get(rd.forward_primer or 0)
        rp = Primers.query.get(rd.reverse_primer or 0)
        fpi = Primers.query.get(self.fp_id)
        rpi = Primers.query.get(self.rp_id)
        return [(rd.round_name, rd.__tablename__, rd.id)] + [(p.name, p.__tablename__, p.id) if p else (None, None, None)for p in (fp, rp, fpi, rpi)]



def reverse_comp(s):
    s=s.upper()
    d = {'A':'T','T':'A','C':'G','G':'C','N':'N'} #dict(zip('ATCGN','TAGCN'))
    comp = [d[i] for i in s[::-1]]
    return ''.join(comp)


def convert_id_to_string(id, base=''):
    c = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    l = id//36
    r = id % 36
    base = c[r] + base
    if l:
        return convert_id_to_string(l, base)
    return base


def convert_string_to_id(s):
    c = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    result = 0
    for k, i in enumerate(s[::-1]):
        result = result + c.index(i.upper())*(36**k)
    return result


def lev_distance(s1, s2, threshold=1000):
    """
    calculate diagonally.stop at threshold. fastest.
    """
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    l1 = len(s1)
    vertical = [0]
    horizontal = [0]
    for i in range(l1):
        char1 = s1[i]
        char2 = s2[i]
        newvertical = [i+1]
        newhorizontal = [i+1]
        for k in range(i):
            if char1 == s2[k]:
                newvertical.append(vertical[k])
            else:
                newvertical.append(
                    1+min(newvertical[-1], vertical[k], vertical[k+1]))
            if char2 == s1[k]:
                newhorizontal.append(horizontal[k])
            else:
                newhorizontal.append(
                    1+min(newhorizontal[-1], horizontal[k], horizontal[k+1]))
        last = vertical[-1] if char1 == char2 else (
            1+min(newvertical[-1], newhorizontal[-1], vertical[-1]))
        newhorizontal.append(last)
        newvertical.append(last)
        currentmin = min(min(newhorizontal), min(newvertical))
        if currentmin > threshold:
            return currentmin
        vertical, horizontal = newvertical, newhorizontal
    horizontal.append(last)
    for index2, char2 in enumerate(s2[l1:]):
        newhorizontal = [index2+l1+1]
        for index1, char1 in enumerate(s1):
            if char1 == char2:
                newhorizontal.append(horizontal[index1])
            else:
                newhorizontal.append(1 + min((horizontal[index1],
                                              horizontal[index1 + 1],
                                              newhorizontal[-1])))
        currentmin = min(newhorizontal)
        if currentmin > threshold:
            return currentmin
        horizontal = newhorizontal
    return horizontal[-1]
