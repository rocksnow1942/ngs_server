from ._twig import Tree,draw,Clade
import json,copy,os,math,pickle
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
import matplotlib.gridspec as gridspec
from mpl_toolkits.mplot3d import Axes3D
from ._utils import lev_cluster,neighbor_join,build_distance_matrix,align_clustered_seq
from ._alignment import Alignment
from itertools import product
from functools import partial
from ._utils import mapdistance,poolwrapper
import textwrap
from inspect import signature
from datetime import datetime
from matplotlib.figure import Figure

"""
Note:
if alignscore is used as a condition, filter will not scan all tree nodes.
will pause at joints where alignscore matches condition and omit its children.
Modified on 2019/09/18
Modified for NGS_server use
Modified for advanced use on 20191201
"""
# TODO
# add count distribution / length distribution /

datareader_API = []
datareader_API_dict = {}

class CallbackDisplay():
    def __repr__(self):
        return "progress_callback"

progress_callback = CallbackDisplay()


def register_API(multithread=False):
    def decorator(func):
        sig = signature(func)
        para = str(sig).replace('self, ', "")
        sigdict = {'name': func.__name__,'multithread':multithread, 'doc':func.__doc__ and func.__doc__.strip(),'defaultpara':para.split('->')[0].strip()[1:-1], 'signature':para}
        datareader_API.append(sigdict)
        datareader_API_dict.update({sigdict['name']:sigdict})
        def wrapper(*args,**kwargs):
            return func(*args,**kwargs)
        wrapper.__signature__ = sig
        wrapper.__name__=func.__name__
        return wrapper
    return decorator 


class Reader(object):
    def ifexist(self,name):
        savefolder=getattr(self,"save_loc",os.getcwd())
        if not os.path.isdir(savefolder):
            os.makedirs(savefolder)
        if os.path.isfile(os.path.join(savefolder,name)):
            print('File {} already exist, add number ~ '.format(name))
            prefix = name.split('.')[0:-1]
            affix=name.split('.')[-1]
            if len(prefix[-1])<3 or prefix[-1][-3]!='~':
                prefix[-1] +='~01'
            else:
                prefix[-1] = prefix[-1][0:-2]+"{:02d}".format(int(prefix[-1][-2:])+1)
            newname='.'.join(prefix+[affix])
            return self.ifexist(newname)
        else:
            return os.path.join(savefolder,name)

##############################################################################
# Data reader module
class DataReader(Reader):
    """
    DataReader class for dealing with ngs data cluster and alignment.
    data store have 5 kinds:
    df or dataframe, store count and percentage information. only store clustered info after self.trim()
    cluster: collection of unique sequences that are closely related to each other.
    joint: alignment from clusters based on neighbor join method.
    align: ensemble of aligned clusters and joints.
    tree: neighbor join tree showed the relative relationship of joint creation.
    """
    # constructor methods
    def __init__(self,name='',filepath=''):
        """
        filepath is at current_app.config['ANALYSIS_FOLDER']/str(analysis.id)
        """
        self.name=name
        self.filepath=filepath
        self.table_name=None
        self.alias={}
        self.processing_para={}
        self.affix = ""
        # self.save_loc= abandoned save location.

    # def exec_command(self,command,args):
    #     """

    #     """
    #     result = eval("self.{}({})".format(command,args))

    @property
    def datestamp(self):
        return datetime.now().strftime('%Y/%m/%d - %H:%M:%S')+'\n'

    @property
    def dr_loc(self):
        return self.filepath

    def __add__(self,b):
        """
        combine DataFrame from two datareader files.
        """
        if b:
            col1=self.df.columns.tolist()
            col2=b.df.columns.tolist()
            assert ('id' in col1) and ('id' in col2), ('Cannot add trimmed DataFrame.')
            return self.copy(df=self.add_df(self.df,b.df))
        else:
            return self.copy()

    def add_df(self,df1,df2):
        result=pd.merge(df1,df2,how='outer',on=['aptamer_seq']).fillna(0)
        result['id']=result.id_x
        result['sum_per'] = result.sum_per_x + result.sum_per_y
        result['sum_count']= result.sum_count_x + result.sum_count_y
        result.drop(labels=['sum_per_x','sum_per_y','sum_count_x','sum_count_y','id_x','id_y'],axis=1,inplace=True)
        return result

    def remove_zero_round(self):
        """
        remove rounds with completely no reading.
        """
        zero=self.df.sum(axis=0)
        zero=zero.loc[zero==0].index.tolist()
        self.df.drop(labels=zero,inplace=True,axis=1)

    def load_from_ngs_server(self, rounds, sequencefilter=lambda x:True, callback=None):
        """
        loads data from ngs server to a dataframe.
        rounds: list of round names to load
        callback: to set progression for display.
        """
        df = self.read_df_from_round(rounds[0])
        if callback: callback(1/(len(rounds)+1)*100)
        for index,r in enumerate(rounds[1:]):
            _df = self.read_df_from_round(r, sequencefilter)
            df=df.merge(_df,how='outer',on=['id','aptamer_seq']).fillna(0)
            if callback:
                callback((2+index)/(len(rounds)+1)*100)
        self.df=df
        df['sum_count'] = df[[i for i in self.list_all_rounds()]].sum(axis=1)
        df['sum_per'] = df[[i+'_per' for i in self.list_all_rounds()]].sum(axis=1)
        return self

    def read_df_from_round(self,r,sequencefilter=lambda x:True):
        """
        helper method for load_from_ngs_server
        """
        data=[(i.sequence.id,i.sequence.aptamer_seq,i.count,i.count/r.totalread*100) for i in filter(sequencefilter,r.sequences)]
        df=pd.DataFrame(data,columns=['id','aptamer_seq',r.round_name,r.round_name+'_per'])
        return df

    @staticmethod
    def revive_tree(name,data):
        """
        rebuild tree from json file
        """
        def revive(data, parent=None):
            tree = Clade(branch_length=data['branch_length'], name=data['name'])
            tree.parent = parent
            for i in data['children']:
                tree.clades.append(revive(i, parent=tree))
            return tree
        return Tree(name=name, root=revive(data))

    def serialize_tree(self):
        """
        jsonify tree into dictonary
        """
        def serialize(tree, result={}):
            for k, i in tree.__dict__.items():
                if isinstance(i, list):
                    result['children'] = []
                    for ele in i:
                        result['children'].append(serialize(ele, {}))
                elif isinstance(i, Clade):
                    pass
                else:
                    result[k] = i
            return result
        return serialize(self.tree.root)

    def jsonify(self,keys='all'):
        todump={}
        keys = self.__dict__.keys() if keys == 'all' else keys
        for k in keys:
            if k == 'tree':
                todump[k]=self.serialize_tree()
            elif 'df' in k:
                todump[k] = self.__dict__[k].to_dict()
            elif k=='align':
                todump[k] = {k: i.to_dict() for k, i in self.__dict__[k].items()}
            else:
                todump[k] = self.__dict__[k]
        return todump

    def saveas(self,name):
        return os.path.join(self.filepath,name)


    def relative_path(self,name):
        """
        create relative path to use in database save of output files. 
        """
        return os.path.join(self.filepath.split('/')[-1],name)

    def save_json(self,affix=""):
        tosave = self.name+affix+'.json'
        with open(self.saveas(tosave),'wt') as f:
            json.dump(self.jsonify(), f, separators=(',', ':'))
        return tosave

    @classmethod
    def load(cls,file):
        if file.endswith('.json'):
            return cls.load_json(file)
        elif file.endswith('.pickle'):
            return cls.load_pickle(file)

    @classmethod
    def load_json(cls, file):
        with open(file, 'rt') as f:
            data = json.load(f)
        for k in list(data.keys()):
            if 'df' in k:
                data[k] = pd.DataFrame(data[k])
            elif k == 'align':
                data[k] = {j: Alignment.from_dict(
                    l) for j, l in data[k].items()}
            elif k == 'tree':
                data[k] = DataReader.revive_tree(
                    name=data['name'], data=data[k])
            else:
                continue
        a = cls()
        a.__dict__.update(data)
        return a

    def save_pickle(self, affix=""):
        """
        affix is used for save pick as "advanced" file
        """
        self.affix = affix = affix or self.affix
        tosave= self.name+affix+'.pickle'
        with open(self.saveas(tosave), 'wb') as f:
            pickle.dump(self, f)
        return tosave

    @classmethod
    def load_pickle(cls, file=''):
        """
        instantiate class from a file.
        """
        with open(file, 'rb') as f:
            return pickle.load(f)

    def sequence_length_hist(self,fullrange=False,save=False):
        if getattr(self,'_df',None) is not None:
            df= self._df
        else:
            df=self.df
        l = df.aptamer_seq.map(len)
        lb=l.quantile(q=0.02)
        up=l.quantile(q=0.98)
        ll = l.max()
        lm=l.min()
        if fullrange:
            bin=[i-0.5 for i in range(int(lm),int(ll)+1)]
        else:
            bin=[i-0.5 for i in range(int(lb)-2,int(up)+2)]
        ax=l.hist(bins=bin,density=1)
        ax.set_xticks([int(i) for i in bin[1::2]])
        ax.set_title('Sequence Length CDF')
        ax.set_xlabel('Length (n.t.)')
        ax.set_ylabel('Frequency')
        if save:
            name = self.name+'LEN_hist.svg'
            tosave=self.saveas(name)
            plt.tight_layout()
            plt.savefig(tosave)
            plt.clf()
            return name

    def sequence_count_hist(self,save=False):
        if getattr(self,'_df',None) is not None:
            df= self._df
        else:
            df=self.df
        ld2 = [i for i in df['sum_count'] for j in range(int(i))]
        bin=np.geomspace(1,int(max(ld2)*1.2),int(max(ld2)*1.2))
        fig,ax=plt.subplots()
        ax.hist(ld2,histtype='step',cumulative=-1,bins=bin)
        ax.set_xscale('log')
        ax.set_title('Read count CDF (reversed)')
        ax.set_xlabel('Read count')
        ax.set_ylabel('Frequency/Total Count')
        ax.ticklabel_format(style='sci', axis='y', scilimits=(1,0))
        ax.grid(True)
        if save:
            name = self.name+'COUNT_hist.svg'
            tosave=self.saveas(name)
            plt.tight_layout()
            plt.savefig(tosave)
            plt.clf()
            return name

    @register_API()
    def filter_df(self,toremove=[],length=None, count=None,per=None,nozeroseq=True,nozeroround=True,savepickle=True) ->"text":
        """
        clean up RAW DataFrame by (If DataFrame is already trimmed, will reset dataframe to Raw DF.)
        1. remove unwanted rounds in <toremove:list> from ngs table.
        2. remove sequence with <length:tuple> outside of length threshold; not use if length=None.
        3. remove sequence with sum count number <= <count:int>
        4. remove sequence with sum percentage <= <per:float>; this is % number, e.g. 0.2 in 0.2% 
        5. remove sequences that have zero count in all rounds if nozeroseq=True 
        5. remove rounds that have zero sequence count if nozeroround=True
        savepickle: whether to save the filtered data.
        """
        if getattr(self, '_df', None) is not None:
            self.df = self._df
        if toremove:
            for i in self.df.columns.tolist():
                if (i in toremove) or (i.rstrip('_per') in toremove):
                    self.df.drop(labels=i,axis=1,inplace=True)
            
        df = self.df
        if length:
            df=df.loc[df.aptamer_seq.apply(lambda x:length[0]<=len(x)<=length[1]),:]
        if count:
            df = df.loc[df.sum_count>=count,:]
        if per:
            df=df.loc[df.sum_per>=per,:]
        df['sum_count']=df[[i for i in self.list_all_rounds()]].sum(axis=1)
        df['sum_per']=df[[i+'_per' for i in self.list_all_rounds()]].sum(axis=1)
        self.df=df
        if nozeroseq:
            self.df=self.df.loc[self.df.sum_count>0,:]
        if nozeroround:
            self.remove_zero_round()
        if savepickle: self.save_pickle()
        return ["{self.datestamp} Current DataFrame: \n {self.df.head()}\n"]

    @register_API(True)
    def df_cluster(self, distance=5, cutoff=(35, 45), count_thre=1, clusterlimit=5000, findoptimal=False, callback=progress_callback, savepickle=True) -> "text,file":
        """
        STEP 1: Cluster sequence in Raw dataframe.
        count_thre: threshold of read to be included.
        cluster limit is the maximum numbers of clusters will allow.
        findoptimal: set to True to search all clusters and find closest cluster for an incoming sequence.
        callback: set to progress_callback to display progress. 
        calling this function on an already clustered analysis will reset dataframe and redo analysis.
        """
        if getattr(self, '_df', None) is not None:
            self.df = self._df
        df = self.df.sort_values(by=['sum_per','sum_count'],ascending=[False,False])
        df = df.loc[df['sum_count']>=count_thre]
        apt_list= df.aptamer_seq.tolist()
        apt_count=df.sum_count.tolist()
        apt_dict,noncluster_count = lev_cluster(apt_list,apt_count,distance=distance,
                                                cutoff=cutoff,clusterlimit=clusterlimit,findoptimal=findoptimal,callback=callback)
        count_dict = dict.fromkeys(apt_dict)
        for key,item in apt_dict.items():
            temp = [[i[0],i[1],df.loc[df.aptamer_seq==i[0]]['id'].item()] for i in item]
            count_dict.update({key:temp})
        self.cluster = count_dict
        self.processing_para.update({'df_cluster':{'distance':distance,'cutoff':cutoff,
                                'count_thre':count_thre,'stop_cluster_index':noncluster_count[0],'stop_cluster_count':noncluster_count[1]}})
        if savepickle:
            savename=self.save_pickle()
        return [f'{self.datestamp} Cluster Done. \n {self.processing_para}'], [self.relative_path(savename)]

    @register_API(True)
    def in_cluster_align(self,cluster_para={'offset':False,'k':4,'count':True,'gap':5,'gapext':1},callback=progress_callback,savepickle=True) ->"text,file":
        """
        STEP 2: Align sequences in each cluster.
        In cluster_para, define following parameters for in cluster align
        offset: whether shift sequence back and forth to find best alignment.
        k: for use in kmmer distance to determine offset value
        count:  consider sequence count weight during alignment
        gap, gapext: penalty score for gap and gap extension.
        callback: set to progress_callback to display progress.
        """
        data = self.cluster
        cluster = align_clustered_seq(data,**cluster_para,callback=callback)
        self.align = cluster
        self.processing_para.update({'cluster_para':cluster_para})
        if savepickle:
            savename=self.save_pickle()
        return [f"{self.datestamp} In cluster align done. \n {self.processing_para}"], [self.relative_path(savename)]

    @register_API(True)
    def build_tree_and_align(self, align_para={'offset': True, 'k': 4, 'count': True, 'gap': 4, 'gapext': 1, 'distance': 'hybrid_distance'}, callback=progress_callback, savepickle=True) -> "text,file":
        """
        STEP 3: Build a tree based on cluster distance by neighbor join and align all clusters together.
        In align_para, define following parameters:
        offset: whether shift sequence back and forth to find best alignment.
        k: for use in kmmer distance to determine offset value
        count:  consider sequence count weight during alignment
        gap, gapext: penalty score for gap and gap extension.
        distance: method for distance calculation, can be: nw_distance or hybrid_distance.
        callback: set to progress_callback to display progress.
        """
        cluster = self.align
        name_list = [i for i,j in cluster.items() if i.startswith('C')]
        alignment_list = [j for i,j in cluster.items() if i.startswith('C')]
        dm = build_distance_matrix(alignment_list,callback=callback,**align_para)
        tree,alignment = neighbor_join(dm,name_list,alignment_list,record_path=True,**align_para,callback=callback)
        tree.name = self.name
        self.tree=tree
        self.align=alignment
        self.processing_para.update({'align_para':align_para})
        if savepickle:
            savename=self.save_pickle()
        return [f"{self.datestamp} Build tree and align done. \n {self.processing_para}"], [self.relative_path(savename)]

    def lazy_build(self,mode='default',save=False): # not used in this version.
        para={'default':[{},{},{}],
              'clus':[dict(distance=3,cutoff=(20,60),count_thre=0,clusterlimit=5000),
                      dict(cluster_para={'offset':False,'k':4,'count':True,'gap':4,'gapext':1}),
                      dict(align_para={'offset':True,'k':4,'count':True,'gap':4,'gapext':1,'distance':'nw_distance'})],
              'seq':[dict(distance=1,cutoff=(20,60),count_thre=0,clusterlimit=5000),
                     dict(cluster_para={'offset':False,'k':4,'count':True,'gap':4,'gapext':1}),
                     dict(align_para={'offset':False,'k':4,'count':True,'gap':4,'gapext':1,'distance':'nw_distance'})]
                }
        self.df_cluster(**para[mode][0])
        self.in_cluster_align(**para[mode][1])
        self.build_tree_and_align(**para[mode][2])
        self.df_trim()

    def tree_guide_align(self,target='root',tree=None,dict_of_alignment=None,start=True,count_=None,replace=True,**kwargs):
        """
        Re-align based on self's tree, will return and update the alignment dict.
        kwargs are for align parameters, include: (default values after =)
        gap=4, gapext=1, offset=True, count=True, k=4 (for kmmer adjust offset)
        the realign will also realign inside cluster alignment.
        """
        if start:
            print('Start aligning...')
            tree = self.tree if target=='root' else self.tree[target]
            t_list = tree._get_terminals()
            data = {i:self.cluster[i] for i in t_list}
            _dict_of_alignment = align_clustered_seq(data,**kwargs)
            count_ = (len(t_list)+1-(len(tree.root.clades)),len(t_list))
        else:
            _dict_of_alignment = dict_of_alignment
        name = tree.root.name
        clade = tree.root.clades
        for i in clade:
            if not _dict_of_alignment.get(i.name,False):
                self.tree_guide_align(tree=i,dict_of_alignment=_dict_of_alignment,start=False,count_=count_,**kwargs)
        if clade:
            align = _dict_of_alignment.get(clade[0].name)
            for i in clade[1:]:
                align=align.align(_dict_of_alignment.get(i.name),name=name,**kwargs)
            _dict_of_alignment.update({str(name):align})
            current = len(_dict_of_alignment.keys())-count_[1]
            print('{} / {} alignment done.'.format(current,count_[0]))
        else:
            pass
        if start:
            if replace:
                self.align.update(_dict_of_alignment)
                self.processing_para['align_para'].update(kwargs)
            return _dict_of_alignment

    def copy(self, **kwargs):
        a = copy.deepcopy(self)
        for key, item in kwargs.items():
            a.__setattr__(key, item)
        return a

    # data clean up methods, run before or after construct a data reader object from scratch.
    @register_API(True)
    def df_trim(self,  savepickle=True) -> "text,file":
        """
        STEP 4: Clean up raw dataframe for later calculations. 
        Remove unused sequence from df. rename and group sequence based on their cluster name.
        calculate the percentage of each joint and append to df.
        df index will be align name like C1 or J1. 
        This step is necessary for downstream analysis.
        """
        df=self.df if getattr(self,'_df',None) is None else getattr(self,'_df')
        seq_list = [i[0] for k in self.cluster.values() for i in k]
        msg=""
        try:
            newdf = df[df.aptamer_seq.isin(seq_list)]
            newdf['aptamer_seq']=newdf['aptamer_seq'].map(lambda x:self.find(x)[0])
            col=newdf.columns.tolist()
            col.remove('aptamer_seq')
            col.remove('id')
            col.remove('sum_per')
            new=newdf.groupby(['aptamer_seq'])[col].apply(lambda x:x.sum())
            self.df=new
            for key in self.align.keys():
                if key.startswith('J'):
                    term = self.tree[key]._get_terminals()
                    self.df.loc[key]=self.df.loc[term].sum(axis=0)
            msg=('DataFrame trim done.')
            self._df=df
        except AttributeError:
            msg=('Dataframe already trimmed.')
        if savepickle:
            savename=self.save_pickle()
        return [f"{self.datestamp} - {msg}"],[self.relative_path(savename)]

    def rename(self, sequence, newname,method='match',**kwargs):
        """
        # change the cluster name in tree and align and cluster
        instead of change name directly, use a dict to map the changes.
        based on the sequence given and rename it to newname.
        method can be 'match' or 'hybrid_distance'/'sw_distance'/'lev_distance'.
        'match' is looking for exact match.
        '??_distance' is thresholding distance.
        related kwargs can be passed for thresholding and distance calculation in self.search.
        if a nucleotide sequence is given, default will only search and change name of clusters, not joints.
        kwargs include method, scope, threshold, and kwargs for distance measure.
        """
        if method=='match':
            hit_ = self.find(sequence)
        else:
            _ = self.search(sequence,method=method,**kwargs)
            hit_=[i[0] for i in _]
        if hit_:
            for hit in hit_:
                self.alias.update({hit:newname})
        else:
            print('{} not found.'.format(newname))

    def _discalc(self,seq,method,kwargs,alignlist):
        return  [i.distances(method)(seq,**kwargs) for i in alignlist]

    @register_API(True)
    def rename_from_known_sequence(self, method='match', threshold=0.1, scope='cluster', alignscore=None, savepickle=True, **kwargs) -> "text":
        """
        Use known aptamer sequence and name to rename clusters in the analysis file.
        method can be 'match',hybrid_distance,nw_distance,sw_distance,lev_distance
        threshold is depend on rename method, how close the cluster distance need to be for it to be renamed. 
        for hybrid_distance,nw_distance,sw_distance: threshold between 0-1
        for lev_distance: threshold 0 - sequence length
        scope can be "cluster" or "align" or "joint". cluster is Cx, joint is Jx, align is combination of C and J.  
        alignscore is a threshold between 0-100 to prevent rename bad alignments. 100 is perfect align. 
        """
        from app.models import KnownSequence
        ks = KnownSequence.query.all()
        ksdict = {i.rep_seq: i.name for i in ks}
        msg = self.rename_from_known(
            ksdict, method=method, threshold=threshold, scope=scope, alignscore=alignscore, **kwargs)
        if savepickle:
            self.save_pickle()
        return [f"Generated on {self.datestamp}"]+["\n".join(msg)]
        

    def rename_from_known(self,knownsequence,method='match',threshold=0.1,scope='cluster',alignscore=None,**kwargs):
        """
        provide KnownSeq object or a string to location of json.
        method can be hybrid_distance,nw_distance,sw_distance,lev_distance
        alignscore is to prevent rename bad alignments.
        """
        msg = []
        if isinstance(knownsequence,str):
            with open(knownsequence,'rt') as f:
                ks = json.load(f)
        elif isinstance(knownsequence,dict):
            ks = knownsequence
        else:
            ks=knownsequence.dict
        ks_list = list(ks)
        old = set(self.alias.keys()) # old alias cluster
        collison=[]
        if method=='match':
            for i,j in ks.items():
                self.rename(i,j,method='match')
        else:
            scope_=self._scope_(scope)
            alignmentslist = [self.align[i] for i in scope_]
            kwargs.update(threshold=threshold) # add threshold info to kwargs to pass to lev_distance.
            distances=[]
            for q in ks_list:
                query = Alignment(q)
                func=partial(query.distances(method=method),**kwargs)
                dis_=poolwrapper(func,alignmentslist,chunks=100)
                distances.append(dis_)
            min_dis_list = [[i_ for i_,k in enumerate(i) if k<=threshold and k ==min(i)] for i in zip(*distances)]
            for i,j in enumerate(min_dis_list):
                toalias = scope_[i]
                aliasname=''
                if len(j)>1: msg.append('Warning: {} have {} possible alias.'.format(toalias,len(j)))
                for k in j:
                    aliasname += ks[ks_list[k]]
                if aliasname:
                    if alignscore and self.align[toalias].align_score()<alignscore:
                        msg.append('{} alignscore {} < {} cannot alias to {}.'
                            .format(toalias,self.align[toalias].align_score(),alignscore,aliasname))
                        continue
                    if toalias not in old:
                        self.alias.update({toalias:aliasname})
                    else:
                        if self.alias[toalias]!=aliasname:
                            collison.append((toalias,aliasname))
                            msg.append('Collison: {} alias collision {} => {}.'.format(
                                toalias, self.alias[toalias], aliasname))
        new = set(self.alias.keys()) - old
        msg.append('Sequence Renamed: ')
        for i in new:
            msg.append(i + ' => '+self.alias[i])
        if collison:
            msg.append('Collision found, rename collison manually if needed.')
        return msg 

    @register_API(True)
    def rename_joint(self, alignscore=70, savepickle=True, ) -> "text":
        """
        rename joint by the already renamed clades (method='heuristic')
        alighscore is the threshold for a joint to be named the same as its parent or children.
        
        if want to rename joint by distance, refer to "rename_from_known_sequence" method.
        """
        msg=[]
        def node_check(node,newdict):
            parent = self.tree._get_parent(node).name
            children = [i.name for i in self.tree[node].clades]
            sister = [i.name for i in self.tree[parent].clades if i.name!=node]
            alias = self.alias[node]
            if self.align[parent].align_score() >= alignscore:
                newalias=alias
                oldalias = self.alias.get(parent,None)
                for i in sister:
                    if i in self.alias.keys() and (sum(self.align[i].count) > sum(self.align[node].count)):
                        newalias = self.alias[i]
                if newalias!=oldalias:
                    newdict.update({parent:newalias})
            for i in children:
                if i not in self.alias.keys():
                    newdict.update({i:alias})
        newdict=self.alias
        while newdict:
            self.alias.update(newdict)
            newdict={}
            for i in self.alias.keys():
                node_check(i,newdict)
            for k,i in newdict.items():
                msg.append(f"{k} => {i}") 
        if savepickle:
            self.save_pickle()
        return [f"Generated on {self.datestamp}"]+["\n".join(msg)]

            # knownsequence=kwargs.get('knownsequence',None)
            # assert knownsequence, ('Must provide known sequence.')
            # self.rename_from_known(knownsequence,method=method,scope='joint',alignscore=alignscore,**kwargs)

    def re_align(self,target,replace=False,**kwargs):
        """
        realign a target node on the tree. with paramethers provided.
        this use the tree_guide_align method. kwargs are align parameters like gap and gapext.
        if replace is Ture, will replace all the children of the node.
        return the alignment object of the target.
        """
        target = self.find(target)[0]
        return self.tree_guide_align(target=target,replace=replace,**kwargs)[target]

    @register_API()
    def normalize_df(self, savepickle=True) -> "text,file":
        """
        normalize percentage of DataFrame to make each round always add up to 100%.
        """
        per=[i for i in self.df.columns if i.endswith('_per')]
        self.df[per]=self.df[per].div(0.01*self.df[per].max(axis=0),axis=1)
        if savepickle:
            savename = self.save_pickle()
        return [f"{self.datestamp} - Dataframe normalized."], [self.relative_path(savename)]

    # utility methods
    def __getitem__(self,name):
        """
        get item will return a new object can be treated as alignment or tree clade,
        for use externally to simplify things.
        """
        a=self.align[self.find(name)[0]]
        # b=self.tree[self.find(name)[0]]
        return AlignClade(a)

    def _scope_(self,scope):
        """
        return list of names in the provided scope.
        """
        if scope=='cluster':
            scope_= self.cluster.keys()
        elif scope=='align':
            scope_= self.align.keys()
        elif scope=='joint':
            scope_=self.align.keys()-self.cluster.keys()
        else:
            print('wrong scope provided, use align scope by default.')
            scope_= self.align.keys()
        return list(scope_)

    @register_API()
    def find_sequence(self,seq="ATCGAGA") -> "text":
        """
        find a sequence with certain n.t. in the cluster and return the name of cluster. (like C1)
        or use the alias name and find the corresponding cluster or joint name. 
        the result is always a list. if multiple names match the alias, will include all and in the order of counts.
        """
        try:
            result = self.find(seq)
            return [f"Generated on {self.datestamp}"]+[", ".join(result)]
        except Exception as e:
            return [f"Generated on {self.datestamp}"]+[f"Error: {e}"]
        
    def find(self, seq):
        """
        find a specific sequence in the alignment and
        return the name of alignment in alignment dict. (like J1 or C1)
        the result is always a list. if multiple names match the alias, will include all and in the order of counts.
        """
        nt = set(['A','G','C','T','-'])
        if set(list(seq)) <= nt:#seq[0] in nt and seq[1] in nt
            seq=seq.replace('-','')
            hit = False
            for key, item in self.cluster.items():
                for i in item:
                    if i[0] == seq:
                        hit = key
                        break
                if hit:
                    return [hit]

        else:
            if seq in self.__dict__.get('alias',{}).values():
                a = [i for i,j in self.alias.items() if j==seq]
                return sorted(a,key=lambda x:sum(self.align[x].count),reverse=True)
            else:
                if seq=='root':
                    return [self.tree.root.name]
                elif seq in self.align.keys():
                    return [seq]
                else:
                    raise KeyError('sequence {} not found.'.format(seq))

    @register_API()
    def translate_sequence(self,seq="C1") -> "text":
        """
        Return the alias name of a Joint or Cluster if there is. 
        """
        return [f"Generated on {self.datestamp}"]+[self.translate(seq)]

    def translate(self,seq):
        if isinstance(seq,str):
            return self.alias.get(seq,seq)
        elif isinstance(seq,list):
            return [(self.translate(i[0]),)+i[1:] for i in seq]

    @register_API(True)
    def search_sequence(self,query="AGCAG",threshold=5,reverse=False,method='lev_distance',scope='cluster',callback=progress_callback,**kwargs)->"text":
        """
        find alignment that match a pattern by its distance to query sequence,
        search scope is within cluster.
        threshold is between 0-1. 0 is looking for exact match. If use Lev_distance, between 0-sequence length. 
        input can be a alignment or sequence
        method can be 'hybrid_distance' or 'sw_distance' or 'lev_distance' or 'nw_distance': latter 3 are time expensive.
        kwargs: pass to distances methods,gap=4, gapext=1, offset=False, count=True 
        callback: set to progress_callback to display progress. 
        """
        result = self.search(query,threshold,reverse,method,scope,callback,**kwargs)
        return [f"Generated on {self.datestamp}"]+["\n".join(["{:>15} : {:<5}".format(i[0],i[1]) for i in result])] if result else ["Nothing found."]

    def search(self,query,threshold=5,reverse=False,method='lev_distance',scope='cluster',callback=None,**kwargs):
        """
        find alignment that match a pattern by its sw_distance,
        search scope is within cluster.
        threshold is between 0-1. 0is looking for exact match.
        input can be a alignment or sequence
        method can be 'hybrid_distance' or 'sw_distance' or 'lev_distance' or 'nw_distance': latter 3 are time expensive.
        kwargs: pass to distances methods,gap=4, gapext=1, offset=False, count=True
        """
        query = Alignment(query) if isinstance(query,str) else query
        query=query.copy()
        result=[]
        scope_=self._scope_(scope)
        scope__=[self.align[i] for i in scope_]
        func=partial(query.distances(method=method),threshold=threshold,**kwargs)
        dis_=poolwrapper(func,scope__,chunks=100,callback=callback,progress_gap=(5,90))
        for key,score in zip(scope_,dis_):
            if score<=threshold:
                result.append((key,score))
        result = sorted(result,key=lambda x:x[1],reverse=reverse)
        return result

    @register_API()
    def tree_path(self,sequence="C1/ATCG",show=['name'])->'text':
        """
        sequence is either a name like C1 or sequence like AGTGA
        find the path of tree joints to root or path between 2 points
        show mode is a list of tags: 'name', 'score', 'count'
        """
        result = self.path(sequence,show)
        return [f"Generated on {self.datestamp}"]+["\n".join([", ".join([str(j) for j in i]) for i in result])]

    
    def path(self, sequence='', show=['name']):
        """
        find the path of tree joints to root or path between 2 points
        show mode is a list of tags: 'name', 'score', 'count'
        """
        if isinstance(sequence, str):
            hit = self.find(sequence)[0]
            _path = self.tree.get_path(hit)
        else:
            hit_a, hit_b = self.find(sequence[0])[0], self.find(sequence[1])[0]
            _path = self.tree.trace(hit_a, hit_b)
        result = []
        for i in show:
            if i == 'name':
                result.append([i.name for i in _path])
            elif i == 'count':
                result.append([sum(self.align[i.name].count) for i in _path])
            elif i == 'score':
                result.append([self.align[i.name].align_score()
                               for i in _path])
        return result

   
    def slice_df(self,round='all'):
        """
        slice off the df by selection round name. round name can be string or a list.
        return the percentage and count DataFrame.
        """
        if round =='all':
            count_=[i for i in self.df.columns.tolist() if (not i.endswith('per')) and i!='sum_count' ]
            per_=[i for i in self.df.columns.tolist() if i.endswith('per')]
        else:
            round = round if isinstance(round,list) else [round]
            if set(round) <= set(self.df.columns.tolist()):
                count_,per_=round,[r+'_per' for r in round]
            else:
                raise ValueError ('wrong round passed in.')
        nd_per,nd_count = self.df[per_],self.df[count_]
        return nd_per,nd_count

    
    def sort_align(self,round='all',scope='cluster'):
        """
        sort cluster based on count or percentage in a round. return list of tuples,
        in form of (cluster name,sum count,sum percentage)
        round can be a list of round names.
        if round = 'all' return all sorted sum counts of clusters and percentage of all rounds.
        """
        res= self.slice_df(round=round)
        nd_per,nd_count = res[0].sum(axis=1),res[1].sum(axis=1)
        return sorted([(i,int(nd_count[i]),nd_per[i]) for i in self._scope_(scope)],key=lambda x:x[1],reverse=True)

    @register_API()
    def filter(self,condition='',listonly=False,scope='align'):
        """
        filter clusters or alignments that satisfy conditions provided.
        if listonly=False, will return (name,count,percentage,alignscore)
        scope = 'align' will search for joints as well.
        condition is string to describe the filter condition,separate by ";" or ",".
        round=['pbs','pbseye_5'];
        1<count<=10;k
        1<sumcount<10
        percent>0.1;
        sumpercent<10;
        alias will include clusters and align with alias that doesn't overlap ;
        aliasonly only return non-overlapping alias.
        alignscore>80; if alignscore used, will only include parent alignments.
        """
        if ';' in condition:
            condition=[i.strip() for i in condition.split(';')]
        elif ',' in condition and '[' not in condition:
            condition=[i.strip() for i in condition.split(',')]
        else:
            condition=[condition.strip()]
        if any([i.startswith('round') for i in condition]):
            round=eval([i.lstrip('round= ') for i in condition if i.startswith('round')][0])
        else:
            round='all'
        result = self.sort_align(round=round,scope=scope)
        nd_per,nd_count = self.slice_df(round=round)

        if any(['alias' in i for i in condition]):
            alias = set([i for i in self.alias.keys() if i.startswith('J')])
            set_toremove=set([i for k in alias for i in self.tree[k]._get_children()])
            aliasonly=[(i,int(nd_count.loc[i].sum()),nd_per.loc[i].sum()) for i in (alias-set_toremove)]
            if 'aliasonly' in condition:
                result=[(i,int(nd_count.loc[i].sum()),nd_per.loc[i].sum()) for i in self.alias.keys() if i not in set_toremove]
            elif 'alias' in condition:
                result = [i for i in result if i[0] not in set_toremove]
                result.extend(aliasonly)
            else:
                print('Alias condition unclear, pass.')
            result.sort(key=lambda x:x[1],reverse=True)


        as_cond=[i for i in condition if 'alignscore' in i]
        if as_cond:
            temp=self._filter_alignscore(as_cond[0])
            result = [i+(temp[i[0]],) for i in result if i[0] in temp.keys()]

        if any(['count' in i for i in condition]):
            count_cond=[i for i in condition if 'count' in i][0]
            newresult = []
            for i in result:
                name = i[0]
                count = nd_count.loc[name].min()
                sumcount=i[1]
                _=newresult.append(i) if eval(count_cond) else 0
            result = newresult

        if any(['percent' in i for i in condition]):
            per_cond=[i for i in condition if 'percent' in i][0]
            newresult = []
            for i in result:
                name = i[0]
                percent = nd_per.loc[name].min()
                sumpercent=i[2]
                _=newresult.append(i) if eval(per_cond) else 0
            result = newresult
        if listonly:
            return [i[0] for i in result]
        else:
            return result

    def _filter_alignscore(self,condition=''):
        """
        filter align and return the parent align with aligh score higher than condition.
        condition = 'alignscore>87'
        use the wrapped function to avoid the need to initialize result each function call.
        format is {name:alignscore}
        """
        def find_clade(tree,condition,result={}):
            a = tree.clades
            alignscore=self.align[tree.name].align_score()
            if eval(condition):
                result.update({tree.name:alignscore})
            else:
                for i in a:
                    find_clade(i,condition,result=result)
            return result
        re = find_clade(self.tree.root,condition=condition,result={})
        return re

    def filter_align(self,condition='',listonly=False,scope='align'):
        """
        method wrap round filter method.
        if condition is a number, can also filter align score higher.
        useful examples:
        'alignscore>=50' will filter out alignment with score >=50, regardless of their counts and round, any Alignments
        that is a sub alignment of another is not included.

        """
        if isinstance(condition,str):
            return self.filter(condition=condition,listonly=listonly,scope=scope)
        else:
            a=str(condition)
            return self.filter(condition='alignscore>'+a,listonly=listonly,scope=scope)
    def filter_cluster(self,condition='',listonly=False,scope='cluster'):
        """
        filter clusters that satisfy conditions provided.
        condition = "round=['pbs','pbseye_5'];count<=10;percent>0.1;alias='V33'"
        """
        return self.filter(condition=condition,listonly=listonly,scope=scope)
    def filter_joint(self,condition='',listonly=False,scope='joint'):
        """
        a method to filter out joints.
        """
        return self.filter(condition=condition,listonly=listonly,scope=scope)

    def filter_tree(self,condition=''):
        """
        TODO
        find clades
        1. terminal joins
        """
        pass

    @register_API()
    def display_all_rounds(self,show=True) -> "text":
        """
        show name of all rounds.
        """
        return [f"Generated on {self.datestamp}"]+[", ".join(self.list_all_rounds())]
    
    def list_all_rounds(self) :
        a=self.df.columns.tolist()
        temp=[]
        for i in a:
            if i not in ['id','aptamer_seq','sum_count']:
                temp.append(i)
        a = [i for i in temp if not i.endswith('per')]
        return a

    def find_align_score(self, r=(90, 100), reverse=True, **kwargs):
        """
        mode=0,1 for align score method.
        count=True,False, to use sequence count or not for calculation.
        if reverse is True, from high to low.
        """
        res = []
        for k, i in self.align.items():
            sc = i.align_score(**kwargs)
            if r[0] <= sc <= r[1]:
                res.append((k, sc))
        return sorted(res, key=lambda x: x[1], reverse=reverse)

    def sub_tree(self,target=[],minimal=False):
        """
        return DataReader object contain minimal tree and minimal alignments,
        if minimal = False, subtree contain all clades.
        if minimal = True, subtree only contain clades that on the path of targets and their direct childre.
        containing all target sequence or alignemnts entered.
        Caution: minimal tree chop off lots of leaf, should be used for plotting only.
        """
        target = [self.find(i)[0] for i in target]
        ca = self.tree.common_ancestor(*target)
        newtree = Tree.from_clade(ca,name=self.name+'_'+ca.name)
        if minimal:
            keep = set()
            for i in target:
                keep.update(newtree.get_path(i))
            def trim(tree, keep):
                if tree.is_terminal():
                    pass
                else:
                    for i in tree.root.clades:
                        if i not in keep:
                            i.root.clades = []
                        else:
                            trim(i, keep)
            trim(newtree, keep)
        cluster = {i:self.cluster.get(i,{}).copy() for i in newtree._get_terminals() if i.startswith('C')}
        table_name = self.name+'_'+ca.name
        align = {i.name:self.align[i.name].copy() for i in newtree.find_clades()}
        alias = {i:self.alias[i] for i in self.alias.keys() if i in align.keys()}
        new = self.copy(tree=newtree,cluster=cluster,align=align,name=table_name,alias=alias)
        return new

    @register_API()
    def list_alias(self,show=True) -> "text":
        """
        list all alias 
        """
        alias = self.alias
        result={}
        for i in set(alias.values()):
            result.update({i:self.find(i)})
        # for k in self.align.keys():
        #     if k[0]!='J' and (k[0] not in 'ACGT') and (k[1] not in 'ACGT'):
        #         if contain in k:
        #             result.append(k)
        m = ["{:>10} : {}".format(k, ', '.join(i)) for k, i in result.items()]
    
        return [f"Generated on {self.datestamp}"]+['\n'.join(m)]

    @register_API()
    def df_info(self,show=True) -> "text,file":
        """
        print the description of dataframe.
        """
        # percentile calculation
        df=self.df.loc[[i.startswith('C') for i in self.df.index],:]
        df_=self._df.loc[:,[i for i in self.df.columns]]
        round_list = df.columns.tolist()
        percentile = []
        for i in round_list:
            temp = df[i][lambda x: x != 0]
            if len(temp)==0:
                temp = [0]
            percentile.append(np.percentile(temp, np.arange(0,120,20)))
        percentile=np.array(percentile).T
        percentile = pd.DataFrame(percentile,index=['Min','20%','40%','60%','80%','Max'],columns=df.columns)
        # unique count, analysis read total read calculation.
        uniquecount = df_.apply(lambda x:x!=0).sum()
        uniquecount.name='Count'
        anaread = df.sum()
        anaread.name='AyRead'
        totalread = anaread.copy()
        totalread.name='TlRead'
        for i in round_list:
            if i.endswith('per'):
                totalread[i]=100.0
            elif i == 'sum_count':
                pass
            else:
                totalread[i]=totalread[i]*100/anaread[i+'_per']
        totalread['sum_count']=totalread[[i for i in round_list if not i.endswith(('_per','_count'))]].sum()
        a=pd.concat([uniquecount,anaread,totalread],axis=1).T
        a=pd.concat([percentile,a],axis=0)
        a[[i for i in round_list if not i.endswith('_per')]]=a[[i for i in round_list if not i.endswith('_per')]].astype(int,errors='ignore')
        if show:
            pd.set_option('display.max_columns', None)
            pd.set_option('display.expand_frame_repr', False)
            a.to_csv(self.saveas('df_info.csv'))
            return [f"Generated on {self.datestamp}"]+[str(a)], [self.relative_path('df_info.csv')]
        else:
            return a


    def df_table(self):
        # in order of name, count, anaread, total read, percent, 80% read, Max read
        """
        used in ngs_server to display df table
        """
        result = []
        df= self.df_info(show=False).to_dict()
        for rn in self.list_all_rounds():
            ar=df[rn]['AyRead']
            tr=df[rn]['TlRead']
            result.append((rn, df[rn]['Count'],ar,tr,"{:.2%}".format(ar/tr),
                df[rn]['80%'],df[rn]['Max']))
        return result

    @register_API()
    def show_cluster_summary(self,show=True) -> "text":
        """
        return summary of cluster info 
        used in ngs_server 
        """
        result = self.cluster_summary() 
        if len(result) > 2:
            result = [result[0]] + ["Percentile: {:>6}, Total Count: {:>10}, Unique count: {:<5}".format(i,j,k) for i,j,k in result[1:]]
            return [f"Generated on {self.datestamp}"]+["\n".join(result)]
        else:
            return [f"Generated on {self.datestamp}"]+result

    
    def cluster_summary(self,) :
        """
        return summary of cluster info 
        used in ngs_server 
        """
        # in order of percentile, count, sequence count.
        result=[]
        cluster=self.__dict__.get('cluster',None)
        if cluster:

            result.append('Total Clusters: {}'.format(len(cluster.keys())))
            count = np.array([sum(k[1] for k in i) for i in self.cluster.values()])
            seqcount = np.array([len(i) for i in self.cluster.values()])
            percent=[0,20,40,60,80,90,100]
            per_c = np.percentile(count,percent)
            per_sc = np.percentile(seqcount,percent)
            for i,j,k in zip(percent,per_c,per_sc):
                result.append((str(i)+" %",int(j),int(k)))
        else:
            result.append('Doesn\'t Contain Cluster.')
        return result

    # tools methods
    @register_API()
    def compare_clusters(self,a='C1',b='V42',format=(1,1,1,5,1,1),**kwargs) -> "text":
        """
        a, b are name of two clusters or joints. 
        align two sequence a and b, print their hybrid distance, and nw distance.
        otherwise return nw alignscore. 
        kwargs are parameters for calculating distance. 
        format in order:
        1. Whether show name of two aligned sequence (C1, C2 etc.).
        2. Whether show count of sequences. 
        3. Whether show the offset of current sequence. 
        4. Whether collapse sequence based on provided distance threshold 
        5. Whether order sequence based on their count. 
        6. show index on top: linking style. 
        """
        a=self.align[self.find(a)[0]] if isinstance(a,str) else a
        b=self.align[self.find(b)[0]] if isinstance(b,str) else b
        align = a.align(b,**kwargs)
        output=[]
        output.append(">>> Compare {} with {} <<<".format(repr(a),repr(b)))
        output.append("nw_align_score: {:.3f}".format(align.align_score()))
        dis = ['hybrid_distance','sw_distance','lev_distance']
        for i in dis:
            output.append("{}: {:.3f}".format(i,a.distances(i)(b,**kwargs)))
        output.append('>>>Alignment: Sequence Collapse Thres: {:<2}{}<<<'.format(format[3],
                        ' '*(len(align)//8*8-33)+'Name\t'*bool(format[0])+
                        'Count\t'*bool(format[1])+'Offset\t'*bool(format[2])))
        output.append(align.format(*format))
        output = '\n'.join(output)
        return [f"Generated on {self.datestamp}"]+[output]
        
    @register_API()
    def show_clusters_in_round(self,round='',top=100,show=True,) -> "text,file":
        """
        show the slice of clusters in a round, ranked by percentage.
        round: name of round.
        top: number of top N to display. Or use (100,200) to slice from top 100 to 200 rank. 
        show: set to False to use avoid display too much. 
        """
        _slice=slice(0,top) if isinstance(top,int) else slice(*top)
        countcol=(self.df.loc[[i for i in self.df.index if i.startswith('C')],
                    [round,round+'_per']].sort_values(by=round,ascending=False))
        ccol = countcol.loc[countcol[round]>0,:].iloc[_slice,:]
        ccol['A.K.A']=ccol.index.map(self.translate)
        ccol['Sequence']=ccol.index.map(lambda x:self.align[x].rep_seq())
        ccol.index.name=None
        ccol.to_csv(self.saveas('show_clusters_in_round.csv'))
        files = [self.relative_path("show_clusters_in_round.csv")]
        if show:
            text = str(ccol)
        else:
            text = "Download to view."
        return [f"Generated on {self.datestamp}"]+[text], files

    
    # def round_align(self,target='',round='all',table=None):
    #     """
    #     show alignment of a target cluster in a specific round.
    #     """
    #     _=self.plot_logo_trend(target=target,rounds=round,plot=False,table=table,save=False)
    #     return _

    @register_API()
    def set_round_order(self,neworder=[],savepickle=True) -> "text":
        """
        rearrange round order by providing the new order of rounds.
        """
        assert set(neworder)==set(self.list_all_rounds()),('Must enter all rounds.')
        new = ['sum_count'] +neworder+[i+'_per' for i in neworder]
        self.df = self.df.loc[:,new]
        if savepickle:
            self.save_pickle()
        return [f"Generated on {self.datestamp}"]+[f"Round order changed to {neworder}"]

    @register_API()
    def call_mutation(self,target="C1",sequence="ATCGA",count=True)->"text":
        """
        find mutations in a target compare to a known sequence
        target is 'Cx' or 'Jx' or an alias name or an sequence can be found in analysis. 
        sequence is a ATCG sequence. 
        """
        seq = Alignment(sequence) if isinstance(sequence, str) else sequence
        a=seq.align(self[self.find(target)[0]].rep_seq(count).replace('-',''),offset=False)
        mutation=[]
        position=0
        for i,(j,k) in enumerate(zip(*a.seq)):
            if j in 'ACGT': position+=1
            if j!=k:
                m = j+str(position)+k
                mutation.append(m)
        return [f"Generated on {self.datestamp}"]+['/'.join(mutation)]

    # method that save txt files
    @register_API()
    def analysis_info(self,show=True) -> "text,file":
        """
        Provide basic information about alignment, dataframe, sequence counts, round name, etc.
        """
        # if save:
        #     _save = self.ifexist('INFO_'+save+'.txt' if isinstance(save,str) else 'INFO_{}.txt'.format(self.name))
        result = []
        content = self.__dict__
        for key,item in content.items():
            if isinstance(item,str):
                result.append(key+': '+item)
        result.append('\n')
        dataframe = content.get('df',None)
        if isinstance(dataframe,pd.DataFrame):
            result.append('DataFrame Summary:')
            pd.set_option('display.max_columns', None)
            pd.set_option('display.expand_frame_repr', True)
            result.append(str(self.df_info(show=False)))
        else:
            result.append('Doesn\'t Contain DataFrame.')
        result.append('\n')
        cluster = content.get('cluster',None)
        if cluster:
            result.append('Cluster Summary:')
            result.append('Total Clusters: {}'.format(len(cluster.keys())))
            count = np.array([sum(k[1] for k in i) for i in self.cluster.values()])
            seqcount = np.array([len(i) for i in self.cluster.values()])
            percent=[0,10,20,30,40,50,60,70,80,90,100]
            per_c = np.percentile(count,percent)
            per_sc = np.percentile(seqcount,percent)
            result.append('Cluster percentile: count / seq_count')
            for i,j,k in zip(percent,per_c,per_sc):
                result.append('Cluster percentile {}%: {} / {}'.format(i,int(j),int(k)))
        else:
            result.append('Doesn\'t Contain Cluster.')
        result.append('\n')
        align = content.get('align',None)
        if align:
            result.append('Align Summary:')
            align_score = np.array([i.align_score() for j,i in align.items() if j not in self.cluster.keys()])
            if align_score.any():
                percent=[0,10,20,30,40,50,60,70,80,90,100]
                per = np.percentile(align_score,percent)
                result.append('Align counts: {}'.format(len(align_score)))
                for i,j in zip(percent,per):
                    result.append('Align Score percentile {}%: {:.2f}'.format(i,j))
        else:
            result.append('Doesn\'t Contain Align.')
        result.append('\n')
        tree = content.get('tree',None)
        if tree:
            result.append('Tree Summary:')
            result.append('Tree name: {}'.format(self.tree.name))
            result.append('Tree terminal counts: {}'.format(len(self.tree._get_terminals())))
        else:
            result.append('Doesn\'t Contain Tree.')
        result.append('\n')
        processpara = content.get('processing_para',None)
        if processpara:
            result.append('Processing Parameters:')
            result.append(json.dumps(processpara,indent=4))
        else:
            result.append('Doesn\'t contain processing parameters.')
        result.append('\n')
        result = '\n'.join(result)
    
        with open(self.saveas('analysis_info.txt'), 'wt') as f:
            f.write(result)
        if not show:
            result = "Download file to view result."
        return [f"Generated on {self.datestamp}"]+[result], [self.relative_path('analysis_info.txt')]

    @register_API()
    def describe_cluster(self, target=[], format=(1, 1, 1, 5, 1, 1), count=True, show=False) -> "text,file":
        """
        target: a single "C1" or a list of clusters. 
        print out information of a joint in the tree: include it's parents and children, it's align score and align.
        format: see compare_clusters for details. 
        count is to change the way rep_seq was calculated. True will consider count of sequence. False will consier unique sequence.  
        Avoid using show=True. 
        """

        target = [target] if isinstance(target,str) else target
        # if save:
        #     _save= 'ALN_'+save+'.txt' if isinstance(save,str) else 'ALN_{}{}.txt'.format(self.translate(target[0]),('_'+str(len(target)-1)+'etc_')*bool(len(target)-1))
        #     _save=self.ifexist(_save)
        target = [self.find(i)[0] for i in target]
        output = []
        for i in target:
            path = self.tree.get_path(i)
            t = path[-1] if len(path)>0 else self.tree.root
            prt = path[-2] if len(path)>1 else self.tree.root
            chd = t.clades
            printlist=[t,prt]
            printlist.extend(chd)
            output.append('>>>Alignment {}, a.k.a. {}<<<'.format(i,self.translate(i)))
            output.append('\tAlign Name, Align Score,Total Count,Unique Count')
            for k,j in zip(['Self','Parent','Child1','Child2','Child3'],printlist):
                output.append('{:>6}: {:>10}, {:>11.2f}, {:>10}, {:>11}'.format(k,self.translate(j.name),self.align[j.name].align_score(count=count),sum(self.align[j.name].count),len(self.align[j.name].seq)))
            output.append('>>>Agglomerated Sequence<<<')
            for k,j in zip(['Self','Parent','Child1','Child2','Child3'],printlist):
                output.append('{:>6}: {}'.format(k,self.align[j.name].rep_seq(count=count)))
            output.append('>>>Alignment: Sequence Collapse Thres: {:<2}{}<<<'.format(format[3],' '*(len(self.align[t.name])//8*8-33)+'Name\t'*bool(format[0])+'Count\t'*bool(format[1])+
            'Offset\t'*bool(format[2])))
            output.append(self.align[t.name].format(*format))
        output = '\n'.join(output)
       
        with open(self.saveas('describe_cluster.txt'), 'wt') as f:
            f.write(output)
        if not show:
            output = "Download file to view result."
        return [f"Generated on {self.datestamp}"]+[output], [self.relative_path('describe_cluster.txt')]

    @register_API()
    def site_correlation(self,target='C1',position=[1,2],show=True) -> "text,file":
        """
        show contigency table of 2 positions of a target alignment.
        caution: the index is 1 based, first position is 1
        """
        align = self.align[self.find(target)[0]]
        i,j=position
        save = self.saveas('site_correlation.csv')
        df = align.correlation(position=position, save=save, show=False)
        return [f"Plot generated on {self.datestamp}"]+[str(df) if show else "Download file to view result."], [self.relative_path('site_correlation.csv')]

    # method that can generate plots
    def _plot_trend(self,result,title,save):
        fig = Figure()
        ax = fig.subplots()
        result.plot(marker='o', title=title , ax = ax)
        ax.set_xticks(range(len(result)))
        result.index.tolist()
        ax.set_xticklabels(result.index.tolist(), rotation=45)
        
        fig.set_tight_layout(True)
        if save:
            fig.savefig(save,format="svg")
            
       

    @register_API()
    def plot_cluster_trend(self, cluster="C1", query='all', plot=True) -> "img,file,text":
        """
        give an tree element name, find its round percentage trend.
        if query is all, find all round percentage, otherwise find rounds in query.
        """
        if query == 'all':
            query = self.df.columns.tolist()
            query = [i for i in query if i.endswith('per')]
        cluster = self.find(cluster)[0]
        result = self.df.loc[cluster][query]
        result.index = [i[:-4] for i in query]
        result.name=self.translate(cluster)
        if plot:
            self._plot_trend(result,self.translate(cluster) + " % Trend",self.saveas("plot_cluster_trend.svg"))
            result.to_csv(self.saveas('plot_cluster_trend.csv'))
            return [self.relative_path("plot_cluster_trend.svg")], [self.relative_path("plot_cluster_trend.csv")], [f"Plot generated on {self.datestamp}"]
        return result

    @register_API()
    def plot_compare_cluster_trend(self,cluster1="C1",cluster2="C2",query='all',  norm=False,) -> "img,file,text":
        """
        plot the ratio trend of two clusters. cluster1/cluster2
        if query is all, find all round percentage, otherwise find rounds in query.
        if norm = True, normalize to max ratio. 
        """
        c1=self.plot_cluster_trend(cluster1,query,plot=False)
        c2=self.plot_cluster_trend(cluster2,query,plot=False)
        ratio=c1/c2
        if norm:
            ratio=ratio/ratio.max()
        self._plot_trend(ratio, self.translate(
            c1.name)+' / '+self.translate(c2.name) + " Trend", self.saveas("plot_compare_cluster_trend.svg"))
        ratio.to_csv(self.saveas("plot_compare_cluster_trend.csv"))
        return [self.relative_path('plot_compare_cluster_trend.svg')], [self.relative_path("plot_compare_cluster_trend.csv")], [f"Plot generated on {self.datestamp}"]

    @register_API()
    def plot_pie(self, top=10, condition='sumcount>10', rank='per', scope='cluster', columns=4, size=2, translate=True,  plot=True,) -> "img,file,text":
        """
        plot the pie chart of selection rounds
        condition is used to filter out align in the plot, if conditon is integer, it wil be intepreted as align score limit.
        if condition is False, will plot top number of clusters based on their count.
        top is how many individuals will be plotted; or a tuple (10,100,step) for slice.
        rank is the criteria for top ranking, will affect which clusters are displayed.
        rank can be : 
        'round': will display each round's higest count separately.
        'per':max percentage in rounds;
        'count': total count in all rounds.
        caution: if not restricting the alignscore in condition, consider change scope to 'cluster' to avoid overlapping.
        columns: how many columns, size: size of each panel. 
        translate: change cluster name to alias. 
        """
       
        per_=[i for i in self.df.columns.tolist() if i.endswith('per')]
        align=self.filter_align(condition,listonly=True,scope=scope)
        if rank=='per':
            nd = self.df[per_].max(axis=1)
            align = sorted(align,key=lambda x:nd[x],reverse=True)
            df = self.df.loc[align,per_]
        else:
            df = self.df.loc[align,per_]
        df.columns=[i[:-4] for i in per_] # rename the columns to round name.
        _slice=slice(0,top) if isinstance(top,int) else slice(*top)
        if plot:
            title= df.columns.tolist()
            layout = (math.ceil(len(title)/columns),columns)
            figsize = (layout[1]*size,layout[0]*size)
            fig = Figure(figsize=figsize)
            axes = fig.subplots(*layout)
            # fig,axes=plt.subplots(*layout,figsize=figsize)
            if layout==(1,1):
                axes = [axes]
            elif layout[0]>1 and layout[1]>1:
                axes = [i for j in axes for i in j]
            for t,ax in zip(title,axes):
                if rank == 'round':
                    col=df[t].sort_values(ascending=False).iloc[_slice]
                else:
                    col=df[t].iloc[_slice]
                col.index=col.index.map(self.translate)
                col.loc['Others']=100-col.sum()
                col.plot.pie(ax=ax,legend=False,title=t,textprops={'fontsize': 4},colormap='tab20')
            for i in axes:
                i.xaxis.set_visible(False)
                i.yaxis.set_visible(False)
                i.spines['top'].set_visible(False)
                i.spines['bottom'].set_visible(False)
                i.spines['right'].set_visible(False)
                i.spines['left'].set_visible(False)
            # plt.tight_layout()
            fig.set_tight_layout(True)
            fig.savefig(self.saveas('plot_pie.svg'), format='svg')
            
            temp_index = df.index.tolist()
            df['Sequence']=[self.align.get(x,Alignment('')).rep_seq() for x in temp_index ]
            df.to_csv(self.saveas("plot_pie_table.csv"))
            return [self.relative_path('plot_pie.svg')], [self.relative_path('plot_pie_table.csv')], [f"Plot generated on {self.datestamp}"]

        df = df.loc[align[_slice],:]
        df.loc['Others'] = 100-df.sum()
        if translate:
            df.index=df.index.map(self.translate)
        return df

    @register_API()
    def plot_cluster_3d(self,top=10,condition=50,scope='align',rank='per',) -> "img,text":
        """
        similar to plot_pie, instead plot on 3d plot.
        refer to plot pie for details. 
        """
        # if save:
        #      _save = save if isinstance(save,str) else '{}_{}_top{}'.format(self.name,condition,top)
        #      _save = self.ifexist('B3D_'+_save+'.svg')
        df = self.plot_pie(top=top,condition=condition,scope=scope,rank=rank,plot=False)
        df = df.iloc[::-1]
        rounds_list = [i[:-4] for i in df.columns.tolist()]
        cluster = df.index.tolist()
        _ys=np.arange(df.shape[1])
        _xs=np.arange(df.shape[0])
        _xx, _yy = np.meshgrid(_xs, _ys)
        xs, ys = _xx.ravel(), _yy.ravel()
        zs = df.values.T.reshape(-1)
        bottom = np.zeros_like(zs)
        fig = Figure(figsize=(8,6))
        ax = fig.add_subplot(111, projection='3d')
        width = 0.3
        depth = 0.4
        cmap = mpl.cm.get_cmap('hsv')
        cs = [cmap(i/(top+2)) for i in range(1,top+2)]*df.shape[1]
        ax.bar3d(xs, ys, bottom, width, depth,zs,shade=True, color = cs,alpha=0.2)
        ax.set_xticks(_xs)
        ax.set_zlabel('Cluster percentage')
        ax.set_yticks(_ys+0.4)
        ax.set_yticklabels(rounds_list,ha='left')
        ax.set_xticklabels(cluster,rotation=45,ha='right')
        fig.set_tight_layout(True)
        fig.savefig(self.saveas('plot_cluster_3d.svg'),format='svg')
        return [self.relative_path('plot_cluster_3d.svg')], [f"Plot generated on {self.datestamp}"]

    def _plot_tree(self, node='root',save=False, label='score,seq_count,count', translate=True,size=None,color='count'):
        """
        label: separate tag with comma. can use 'seq,seq_count,score,count'
        size: auto choose size between 10-30 in height, 10 width. or specify size.
        color: how to label color, methods separated by comma, color = 'count,alias,roundname'
        'count' label based on ranking of total count in all rounds; 'roundname' label based on count in a certain round; 
        'alias' label indicate the alias alignments; 'None' no labeling.        
        """
        def wrap(self, method):
            def short(x):
                if translate:
                    result=self.translate(x.name)
                else:
                    result= x.name+'/'+self.translate(x.name) if x.name!=self.translate(x.name) else x.name
                return result
            def count(x):
                return str(sum(self.align[x.name].count))
            def score(x):
                return '{:.1f}'.format(self.align[x.name].align_score(mode=1))
            def seq_count(x):
                return str(len(self.align[x.name].seq))
            method = method.split(',')
            def result(x):
                r=short(x) if len(method)==0 else short(x)+':'
                for k,i in enumerate(method):
                    if i == 'count':
                        r+='/'*bool(k)+count(x)
                    elif i == 'score':
                        r+='/'*bool(k)+score(x)
                    elif i == 'seq_count':
                        r+='/'*bool(k)+seq_count(x)
                    elif i=='seq':
                        r+='/'*bool(k)+str(x)
                    else:
                        r+='Wrong Label Format.'
                return r
            return result

        # if save:
        #     save=self.ifexist(('TREE_'+node+'.svg') if isinstance(save, bool) else 'TREE_'+save+'.svg')
        if node != 'root':
            p = Tree(root=self.tree[self.find(node)[0]], name=self.tree.name+'_'+node,)
        else:
            p = self.tree
            node = self.tree.name
        p.ladderize()
        calc_size=(10,min(max(10,0.1*len(p._get_terminals())),30))
        size = size if size else calc_size

        def mapper(c,palette):
            """
            c is a sorted list of label value pair, return color mapper dict.
            """
            cmap = mpl.cm.get_cmap(palette)
            new_c=[]
            index=0
            for i,j in enumerate(c):
                if j[1]!=c[i-1][1]:
                    index+=1
                new_c.append((j[0],index))
            m=new_c[-1][1]
            color={i:cmap(1-j/m) for i,j in new_c}
            return color

        # determin color label to use
        colormap={}
        if 'count' in color:
            c = self.sort_align()
            colormap.update(mapper(c,'cool'))
        if 'alias'in color:
            colormap.update(dict.fromkeys(self.alias,'red'))
        if color in self.df.columns.tolist() or isinstance(color,list):
            c=self.sort_align(color)
            colormap.update(mapper(c,'cool'))
        draw(p, do_show=not save, save=save,
             label_func=wrap(self, label), size=size,label_colors=colormap,colorbar=True if colormap else False)

    @register_API(True)
    def plot_tree(self,node='J111',condition='',scope='cluster',mode='minimal',**kwargs) -> "img,text":
        """ 
        node: node='root' will plot whole tree, set to a Jx to plot only below that joint, or set to an alias name.  
        condition passed to filter_cluster method to filter the clusters to plot. set to "" will bypass filter. 
        if mode is 'minimal', the tree will only contain fitltered clusters (trimmed); 'full', the tree will be every nodes.
        kwargs options: 
        label: separate tag with comma. can use 'seq,seq_count,score,count'
        size: auto choose size between 10-30 in height, 10 width. or specify size.
        color: how to label color, methods separated by comma, color = 'count,alias,roundname'
        'count' label based on ranking of total count in all rounds; 'roundname' label based on count in a certain round; 
        'alias' label indicate the alias alignments; 'None' no labeling.   
        """
        if condition:
            target= self.filter(scope=scope,condition=condition,listonly=True)
            tree=self.sub_tree(target,minimal=(mode=='minimal'))
        else:
            tree = self
       
        node = self.tree.common_ancestor(*self.find(node)).name
        tree._plot_tree(node=node, save=self.saveas('plot_tree.svg'), **kwargs)
        return [self.relative_path('plot_tree.svg')], [f"Generated on {self.datestamp}"]

    @register_API()
    def plot_correlation(self,target='C1',**kwargs) -> "img,file,text":
        """
        plot correlation matrix of an alignment, using only unique sequences.
        for theils_u, the plot is given x cordinate sequence, predictability of y cordinate.
        plot options in kwargs:
        theil_u=True/False to use theils_u or cramers_v.
        cmap='YlGnBu' for gree - yellow color
        annot = True for annotate correlation numbers
        linewidth = 0.1 for showing the grid line
        figsize = (10,8) for figure size.
        """
        align = self.align[self.find(target)[0]]
        corr=align.plot_correlation(save=self.saveas('plot_correlation.svg'),return_results=True,**kwargs) 
        corr.to_csv(self.saveas('plot_correlation_matrix.csv'))
        return [self.relative_path('plot_correlation.svg')], [self.relative_path('plot_correlation_matrix.csv')], [f"Plot generated on {self.datestamp}"]

    @register_API()
    def plot_logo(self,target='C1',save=True,count=True) -> "img,text":
        """
        plot logo of a specific target cluster.
        count: use count weight.
        """
        # if save:
        #     _save = self.ifexist('LOGO_'+save+'.svg' if isinstance(save,str) else 'LOGO_'+target+'.svg')
        align=self.align[self.find(target)[0]]
        if save:
            align.dna_logo(save=self.saveas('plot_logo.svg'),show=False,count=count)
            return [self.relative_path('plot_logo.svg')], [f"Plot generated on {self.datestamp}"]
        else:
            fig=align.dna_logo(save=False,show=False,count=count)
            return fig

    @register_API(True)
    def plot_heatmap(self,top=50,condition='sumcount>10',scope='cluster',order='per',norm=0,contrast=1,labelthre=0.0001,callback=progress_callback) -> "img,file,text":
        """
        plt heatmap of cluster percentage in all rounds.
        condition: refer to filter for details. 
        contrast is an interger>=1, for enhancing low percentage sequence.
        order can be 'per'/'??_distance'/'trend' to sort the cluster along y axis based on percentage or distance or trend.
        Order can also be a formula to calculate a score using round names. E.g. : order = 'Round1 / Round2 + Round3/Round2'.
        '??_distance' is the distance method, 'nw_distance'/'hybrid_distance'/'lev_distance'
        if norm = 0, normalize is based on the whole dataframe, using original percentage.
        if norm = 1, normalize along x axis to make biggest number 1.
        exp: condition='alias,sumcount>0',scope='cluster'
        set callback=progress_callback to show progress.
        """
        img,file =self._plot_heatmap(top,condition,scope,order,norm,contrast,labelthre,callback,returndf=False) 
        return img,file,[f"Plot Heatmap on {self.datestamp}"]

    
    def _plot_heatmap(self,top=50,condition='sumcount>10',scope='cluster',order='per',norm=0,contrast=1,labelthre=0.0001,callback=None,returndf=False):
        """
        plt heatmap of cluster percentage in all rounds.
        contrast is an interger>=1, for enhancing low percentage sequence.
        order can be 'per'/'??_distance'/'trend' to sort the cluster along y axis based on percentage or distance or trend.
        '??_distance' is the distance method, 'nw_distance'/'hybrid_distance'/'lev_distance'
        if norm = 0, normalize is based on the whole dataframe, using original percentage.
        if norm = 1, normalize along x axis to make biggest number 1.
        exp: condition='alias,sumcount>0',scope='cluster'
        """
        # check if save location is legit first
        # if save:
        #     _save_= save if isinstance(save,str) else '{}_{}_top{}{}{}'.format(self.name,condition,top,order,'norm'*norm)
        #     _save_=self.ifexist('HEAT_'+_save_+'.svg')
        # if savedf:
        #     _savedf_ = savedf if isinstance(savedf,str) else '{}_{}_top{}{}{}'.format(self.name,condition,top,order,'norm'*norm)
        #     _savedf_=self.ifexist('TAB_'+_savedf_+'.csv')
        # preprocess data frame for plotting.
        df = self.plot_pie(top=(0,None),condition=condition,scope=scope,plot=False,translate=False).drop(labels='Others',axis=0)
        if norm:
            df = df.div(df.max(axis=1),axis=0)

        _slice = slice(0, top) if isinstance(top, int) else slice(*top)
        # set index order according to order option. return a new_index list
        index = df.index.tolist()
        order_score = None
        if ('distance' in order) or (order=='trend'):
            index = index[_slice]
            
            new_index = [index.pop(0)]
            startlength= len(index)
            while index:
                if callback:
                    callback((startlength-len(index))/startlength * 100, start=5, end=90)
                score = 1e9
                _index = index[0]
                for i in index:
                    if 'distance' in order:
                        t = self.align[i].distances(method=order)(self.align[new_index[-1]])
                    elif order == 'trend':
                        t = ((df.loc[i]/df.loc[i].max()-df.loc[new_index[-1]]/df.loc[new_index[-1]].max())**2).sum()
                    else:
                        t = 1e10
                    if t<score:
                        score = t
                        _index = i
                new_index.append(_index)
                index.remove(_index)
        elif order == 'per':
            new_index = index 
        else: # calculate score column 
            old_df = df.copy() 
            for c in df.columns: # first fill 0 in the dataframe with minimal value in each column. 
                df[c]=df[c].replace([0],df[c].replace(to_replace=[0],value=1).min())

            # calculate score column
            roundlist = self.list_all_rounds()
            exes = order
            for r in roundlist:
                exes = exes.replace(r, f"df['{r}']")
            order_score = eval(exes)
            new_index = order_score.sort_values(ascending=False).index.to_list()
            df = old_df # swap back df to with 0s. 

        df = df.loc[new_index]
        
        # start plotting  only top n values
        
        df_slice = df.loc[new_index[_slice], :]
        correction = 1 if norm else 100
        df_np = np.flip((df_slice.values/correction)**(1/contrast), axis=0)
        rounds = df_slice.columns.tolist()
        # translate C1 to alias names.
        cluster = df_slice.index.map(self.translate).tolist()
        fig = Figure(figsize=(max(8,round(len(rounds)*0.7)),min(12,max(5,0.4*len(cluster)))))
        gs = gridspec.GridSpec(1,max(9,round(len(rounds)*0.8)),fig)
        ax = fig.add_subplot(gs[0,:-1])
        df_np=df_np[::-1]
        ax.imshow(df_np,aspect='auto',cmap='YlGnBu')
        # label block value
        if labelthre:
            for i,j in product(range(df_np.shape[0]),range(df_np.shape[1])):
                real_ = df_np[i,j]**contrast
                if real_>labelthre:
                    colo='dimgrey' if df_np[i,j]<0.3 else 'w'
                    ax.text(j, i, '{:.2f}'.format(real_*100),ha="center", va="center", color=colo)
        ax.set_xticks(np.arange(len(rounds)))
        ax.set_ylim(-0.5,len(cluster)-0.5)
        ax.set_yticks(np.arange(len(cluster)))
        ax.set_xticklabels(rounds,rotation=45, ha="right",
                 rotation_mode="anchor")
        cluster.reverse()
        top=len(cluster)
        if len(cluster)<=70:
            ax.set_yticklabels(cluster[::-1])
        else:
            cluster = [i if (i in self.alias.values()) or k%(len(cluster)//20)==0 else '' for k,i in enumerate(cluster)]
            ax.set_yticklabels(cluster)
        ax.set_title('{}\n{}\ntop{}#{}#{}#ct{}'.format(self.name,'\n'.join(textwrap.wrap(condition,60)),top,order,'no-'*(1-norm)+'norm',contrast))
        gradient = np.linspace(0, 1, 256)
        gradient = np.vstack((gradient,gradient)).T
        cax = fig.add_subplot(gs[0,-1])
        cax.imshow(gradient,aspect='auto',cmap='YlGnBu')
        cax.set_xlim(0,2.2)
        cax.set_ylim(-85,256+85)
        cax.text(-0.5,-10,'Low',fontsize=12)
        cax.text(-0.5,259,'High',fontsize=12)
        cax.set_yticks(np.arange(0,257,25.6))
        cax.set_yticklabels(['{:.1f}'.format(i) for i in np.arange(0,1.05,0.1)])
        cax.set_xticks([0])
        cax.set_xticklabels([''])
        cax.spines['top'].set_visible(False)
        cax.spines['bottom'].set_visible(False)
        cax.spines['right'].set_visible(False)
        cax.spines['left'].set_visible(False)
        cax.tick_params(axis='both', which='both', bottom=False, top=False,
                labelbottom=True, left=True, right=False, labelleft=True)
        # cax.set_axis_off()

        fig.set_tight_layout(True)
        fig.savefig(self.saveas('plot_heatmap'+self.affix+'.svg'),format='svg')

        if returndf:
            return [self.relative_path('plot_heatmap'+self.affix+'.svg')],df_slice
        else:
            if order_score is not None:
                df['Score: '+order] = order_score
            df['Sequence']=df.index.map(lambda x: self.align[x].rep_seq())
            new= self.df.loc[df.index,:]
            df=pd.concat([df,new],axis=1)
            df.index=df.index.map(self.translate)
            df.to_csv(self.saveas('plot_heatmap'+self.affix+'.csv'))
            return [self.relative_path('plot_heatmap'+self.affix+'.svg')], [self.relative_path('plot_heatmap'+self.affix+'.csv')]

    @register_API(True)
    def plot_logo_trend(self,target='C1',rounds='all',format=(1, 1, 1, 3, 1, 1)) -> "img,file,text":
        """
        plot DNA_LOGO trend in all rounds; or provide a list of rounds ['round1','round2'] and will only
        plot LOGO for the provided rounds.
        format is for formatting alignment text. refer to compare_clusters for details. 
        """
        # if save:
        #     _save_=self.ifexist('LOTR_'+save+'.svg' if isinstance(save,str) else 'LOTR_'+target+'.svg')

        align = self.align[self.find(target)[0]].copy()
        seq = [i.replace('-','') for i in self.align[self.find(target)[0]].seq]
        offset = self.align[self.find(target)[0]].offset
        seq = [s[-o:]+s[:-o] for s,o in zip(seq,offset)]
        rounds=self.list_all_rounds()
        df = self._df.loc[self._df.aptamer_seq.isin(seq) ,:]
        nonzero = df.loc[:,rounds].sum(axis=0)
        nonzero = nonzero.loc[nonzero>0].index.tolist()
        
        fig = Figure(figsize=(8,1*(len(nonzero) + 1*(len(nonzero)!=len(rounds)))))
        ax = fig.subplots((len(nonzero) + 1*(len(nonzero) != len(rounds))),1)
            
        alignmentdict=dict.fromkeys(nonzero)
        for axindex,r in enumerate(nonzero):
            align.count=[df.loc[df.aptamer_seq==i,r].item() for i in seq]
            percent = 0
            for _ in seq:
                percent +=df.loc[df.aptamer_seq==_,r+'_per'].item()
            title ='{} in {}, Read: {}, Percent: {:.2f}%'.format(target,r,int(sum(align.count)),percent)
            align.refresh_freq()
            align.name= title
            align.dna_logo(save=False,show=False,ax=ax[axindex])
            alignmentdict.update({r:align.copy().remove_null()})
        if len(nonzero)!=len(rounds):
            ax[-1].set_title('{} doesn\'t exist in following rounds:'.format(target))
            nonex = [i for i in rounds if i not in nonzero]
            lll=0
            nonexist =''
            while nonex:
                _=nonex.pop(0)
                nonexist +=(_+'   ')
                lll+=len(_)
                if lll>40:
                    nonexist+='\n'
                    lll=0
            ax[-1].text(0.5,0.5,nonexist, transform=ax[-1].transAxes, fontsize=10,va='center',ha='center') #bbox=props
            ax[-1].set_axis_off()
        
        with open(self.saveas('plot_logo_trend.txt'),'wt') as f:
            for k,a in alignmentdict.items():
                f.write(f">>> Cluster {target} in round {k} <<<\n\n")                
                f.write(a.format(*format))
                f.write('\n\n'+'*'*70+'\n\n')
    
        fig.set_tight_layout(True)
        fig.savefig(self.saveas('plot_logo_trend.svg'),format='svg')

        return [self.relative_path('plot_logo_trend.svg')], [self.relative_path('plot_logo_trend.txt')], [f"Generated on {self.datestamp}"]
           
##############################################################################


# sub class of DataReader, specialized for deal with single sequence clusters.

# class ClusReader(DataReader):
#     """
#     for read all sequence in the NGS database that is close to a sequence, and analyse
#     light weight tool to quick analyse and cluster sequences on the go.
#     """
#     @property
#     def dr_loc(self):
#         return os.path.join(self.working_dir,'raw_data',self.name+'.clusreader')

#     @classmethod
#     def from_seq(cls,name='UnknownSeq',seq='',dr=None):
#         """
#         build a simple cluster reader file from list of sequence.
#         """

#         dr = dr.working_dir if isinstance(dr,DataReader) else dr
#         result=cls(name=name,working_dir=dr,save_loc='new_analysis',temp=not dr)
#         sequence = seq.split() if isinstance(seq,str) else seq
#         input = [{'id':i,'aptamer_seq':j,'sum_per':100/len(sequence),'sum_count':1,name:1} for i,j in enumerate(sequence)]
#         result.df=pd.DataFrame(input)
#         return result

#     @classmethod
#     def from_dr(cls,target='',count=2,dis=10,dr=None,table=None):
#         """
#         query and build cluster reader from NGS database and query target.
#         search for sequence with read >= count, lev distance <= dis
#         """
#         table = table or dr.table_name
#         result=cls(name=target,working_dir=dr.working_dir if isinstance(dr,DataReader) else dr,
#                         save_loc='new_analysis',temp=not dr)
#         target = dr[target].rep_seq().replace('-','') if isinstance(dr,DataReader) else target
#         result.table_name=table
#         query = """SELECT aptamer_seq from self.table Where sum_count >= {}""".format(count)
#         sql=Mysql().connect().set_table(result.table_name)
#         sequences = [i['aptamer_seq'] for i in sql.query(query).fetchall()]
#         print("Searching {} sequences...".format(len(sequences)))
#         distances= mapdistance(target,sequences,dis,showprogress=True)
#         selected = [i for i,j in zip(sequences,distances) if j<=dis]
#         result.df=sql.search_seq(seq=selected)
#         sql.close()
#         print("Done. {} matching sequences found.".format(len(selected)))
#         return result

#     @classmethod
#     def from_ngs(cls,name='NewSequence',seq='',count=2,dis=10,table=None,dr=None):
#         """
#         generate a DataReader file from sequence and NGS table.
#         provide a save path to dr or use datareader file's save path if provide as dr.
#         need to provide a table or DataReader instance to infer table_name
#         """
#         table = table or dr.table_name
#         table = table if isinstance(table,list) else [table]
#         a=0
#         for i in table:
#             a=cls.from_dr(target=seq,count=count,dis=dis,table=i,dr=dr)+a
#         a.name=name
#         return a

#     @classmethod
#     def empty_like(cls,name='new',dr='',table=None):
#         table = table or dr.table_name
#         result=cls(name=name,working_dir=dr.working_dir if isinstance(dr,DataReader) else dr,
#                         save_loc='new_analysis',temp=not dr)
#         result.table_name=table
#         return result


#################################################

class AlignClade(Alignment,Clade):
    """
    can hold alignment and clade information.
    """
    def __init__(self,*a):
        for b in a:
            for i,j in b.__dict__.items():
                setattr(self,i,j)
