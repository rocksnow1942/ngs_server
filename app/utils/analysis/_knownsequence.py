import pandas as pd
from ._alignment import Alignment,lev_distance
# from ._utils import lev_distance
import copy
# from Levenshtein import distance as lev_distance



defaultloc='/Users/hui/Documents/ngs_data/known_seq.csv'


class KS_Alignment(Alignment):
    def __init__(self,*args,**kwargs):
        self.ks=kwargs.pop('knownseq')
        self.__dict__['note'] =kwargs.pop('note')
        self.__dict__['target'] =kwargs.pop('target')
        super().__init__(*args,**kwargs)

    def __setattr__(self,name,value):
        if name in ['alias','target','note','aptamer_seq']:
            name = 'name' if name=='alias' else name
            self.ks.df.loc[self.ks.df.name==self.name,name]=value
        else:
            self.__dict__[name]=value
    def copy(self):
        self.ks=None
        return copy.copy(self)
    @property
    def info(self):
        result = '\n'.join(['Name: '+self.name,'Sequence: '+self.seq[0],'Target: '+self.target,'Note: '+self.note])
        print(result)



class KnownSeq():
    def __init__(self,csv_loc=None,ks=None):
        if ks:
            data=[(i.rep_seq,i.name,i.target,i.note) for i in ks]
            self.df=pd.DataFrame(data,columns=['aptamer_seq','name','target','note'])
            self.csv_loc=csv_loc
        else:
            csv_loc = csv_loc or defaultloc
            self.df=pd.read_csv(csv_loc,skip_blank_lines=True).dropna(axis=0, how='all').fillna('')
            self.csv_loc=csv_loc
            self.df.aptamer_seq = self.df.aptamer_seq.map(lambda x:x.strip().replace(' ',''))
            assert len(set(self.df.name))==len(self.df.name),('Aptamer name not unique.')

    def save(self):
        self.df.to_csv(self.csv_loc,index=False)

    def __getattr__(self,attr):
        if attr in self.df.name.tolist():
            return KS_Alignment(knownseq=self,sequence=self.df.loc[self.df.name==attr,'aptamer_seq'].tolist(),
                            count=[10],name=attr, target=self.df.loc[self.df.name==attr,'target'].item(),
                            note=self.df.loc[self.df.name==attr,'note'].item())
        else:
            print("{} is not in KnownSeq.".format(attr))


    def __getitem__(self,item):
        return self.__getattr__(item)

    @property
    def dict(self):
        return dict(zip(self.df.aptamer_seq,self.df.name))

    @property
    def names(self):
        return self.df.name.tolist()

    @property
    def sequences(self):
        return self.df.aptamer_seq.tolist()

    def find(self,sequence,top=5):
        """
        find a known sequence with most similarity to the query.
        """
        sequence = sequence if isinstance(sequence,str) else sequence.rep_seq().replace('-','')
        return sorted([(i,j,lev_distance(i,sequence)) for i,j in zip(self.df.aptamer_seq,self.df.name)],key=lambda x:x[2])[0:top]

    def add(self,seq='',name='',target='',note='N/A'):
        seq=seq.strip().replace(' ','')
        assert set(seq)<=set('ACTG') and seq not in self.df.aptamer_seq.tolist(), ('Sequence not valid')
        assert name and (name not in self.df.name.tolist()),('Must enter a valid name.')
        assert target,('Must enter a valid target name.')
        self.df=self.df.append({'aptamer_seq':seq,'name':name,'target':target,'note':note},ignore_index=True)

    def delete(self,name=''):
        self.df = self.df.loc[self.df.name!=name,:]
