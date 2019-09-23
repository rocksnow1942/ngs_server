from ._twig import Tree,draw,Clade
import pickle,json,copy,os,math
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

"""
Note:
if alignscore is used as a condition, filter will not scan all tree nodes.
will pause at joints where alignscore matches condition and omit its children.

Modified on 2019/09/18
Modified for NGS_server use

"""
# TODO
# add count distribution / length distribution / 

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
        filepath is the folder path for all cache files.
        """
        self.name=name
        self.filepath=filepath
        self.table_name=None
        self.alias={}
        self.processing_para={}
        # self.save_loc= abandoned save location.
                    

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

    
    def load_from_ngs_server(self,rounds,callback=None):
        import time
        df = self.read_df_from_round(rounds[0])
        if callback: callback(1/(len(rounds)+1)*100)
        for index,r in enumerate(rounds[1:]):
            ###
            time.sleep(5) ###testing
            _df = self.read_df_from_round(r)
            df=df.merge(_df,how='outer',on=['id','aptamer_seq']).fillna(0)
            if callback:               
                callback((2+index)/(len(rounds)+1)*100)
        self.df=df
        df['sum_count'] = df[[i for i in self.list_all_rounds()]].sum(axis=1)
        df['sum_per'] = df[[i+'_per' for i in self.list_all_rounds()]].sum(axis=1)
        self.df=df
        return self

    def read_df_from_round(self,r):
        data=[(i.sequence.id,i.sequence.aptamer_seq,i.count,i.count/r.totalread*100) for i in r.sequences]
        df=pd.DataFrame(data,columns=['id','aptamer_seq',r.round_name,r.round_name+'_per'])
        return df

    def jsonify(self):
        todump={}
        for k,item in self.__dict__.items():
            if k == 'tree':
                continue
            elif 'df' in k:
                todump[k]=item.to_dict()
            elif k=='align':
                todump[k]={k:i.to_dict() for k,i in item.items()}
            else:
                todump[k]=item
        return todump

    def save_json(self):
        with open(os.path.join(self.filepath,self.name+'.json'),'wt') as f:
            json.dump(self.jsonify(),f)

    @classmethod
    def load_json(cls,file):
        with open(file,'rt') as f:
            data=json.load(f)
        for k in data:
            if 'df' in k:
                data[k] = pd.DataFrame(data[k])
            elif k=='align':
                data[k] = {j:Alignment.from_dict(l) for j,l in data[k].items()}
            else:
                continue
        a=cls()
        a.__dict__=data
        return a

    def sequence_length_hist(self,fullrange=False):
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
        l.hist(bins=bin,density=1)

    def filter_df(self,toremove=[],length=None, count=None,per=None,nozero=True):
        """
        clean up raw df by
        1.remove unwated columns from ngs table.
        2. remove sequence with length outside of length threshold
        3. remove sequence with sum count number <= count
        4. remove sequence with sum percent <= per
        and remove zero count sequences
        """
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
        if nozero:
            self.df=self.df.loc[self.df.sum_count>0,:]
        print('Current Dataframe:')
        print(self.df.head())

    def df_cluster(self,distance=5,cutoff=(35,45),count_thre=1,clusterlimit=5000,findoptimal=False):
        """
        cluster sequence in self.df.
        cluster limit is the maximum of clusters it will give.
        """
        df = self.df
        df = df.loc[df['sum_count']>=count_thre]
        apt_list= df.aptamer_seq.tolist()
        apt_count=df.sum_count.tolist()
        apt_dict,noncluster_count = lev_cluster(apt_list,apt_count,distance=distance,
                                                cutoff=cutoff,clusterlimit=clusterlimit,findoptimal=findoptimal)
        count_dict = dict.fromkeys(apt_dict)
        for key,item in apt_dict.items():
            temp = [[i[0],i[1],df.loc[df.aptamer_seq==i[0]]['id'].item()] for i in item]
            count_dict.update({key:temp})
        self.cluster = count_dict
        self.processing_para.update({'df_cluster':{'distance':distance,'cutoff':cutoff,
                                'count_thre':count_thre,'stop_cluster_index':noncluster_count[0],'stop_cluster_count':noncluster_count[1]}})
        

    def in_cluster_align(self,cluster_para={'offset':False,'k':4,'count':True,'gap':5,'gapext':1}):
        data = self.cluster
        cluster = align_clustered_seq(data,**cluster_para)
        self.align = cluster
        self.processing_para.update({'cluster_para':cluster_para})
        

    def build_tree_and_align(self,align_para={'offset':True,'k':4,'count':True,'gap':4,'gapext':1,'distance':'hybrid_distance'},save=True):
        cluster = self.align
        name_list = [i for i,j in cluster.items() if i.startswith('C')]
        alignment_list = [j for i,j in cluster.items() if i.startswith('C')]
        dm = build_distance_matrix(alignment_list,**align_para)
        tree,alignment = neighbor_join(dm,name_list,alignment_list,record_path=True,**align_para)
        tree.name = self.name
        self.tree=tree
        self.align=alignment
        self.processing_para.update({'align_para':align_para})
        if save:self.save()

    def lazy_build(self,mode='default',save=False):
        para={'default':[{},{},{}],
              'clus':[dict(distance=3,cutoff=(20,60),count_thre=0,clusterlimit=5000),
                      dict(cluster_para={'offset':False,'k':4,'count':True,'gap':4,'gapext':1}),
                      dict(align_para={'offset':True,'k':4,'count':True,'gap':4,'gapext':1,'distance':'nw_distance'})],
              'seq':[dict(distance=1,cutoff=(20,60),count_thre=0,clusterlimit=5000),
                     dict(cluster_para={'offset':False,'k':4,'count':True,'gap':4,'gapext':1}),
                     dict(align_para={'offset':False,'k':4,'count':True,'gap':4,'gapext':1,'distance':'nw_distance'})]
                }
        self.df_cluster(**para[mode][0],save=save)
        self.in_cluster_align(**para[mode][1],save=save)
        self.build_tree_and_align(**para[mode][2],save=save)
        self.df_trim()

    def tree_guide_align(self,target='root',tree=None,dict_of_alignment=None,start=True,count_=None,replace=True,**kwargs):
        """
        Re-align based on self's tree, will return and update the alignment dict.
        kwargs are for align parameters, include: (defalut values after =)
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
    def df_trim(self,save_df=True):
        """
        Remove unused sequence from df. rename and group sequence based on their cluster name.
        calculate the percentage of each joint and append to df.
        df index will be align name like C1 or J1.
        """
        df=self.df
        seq_list = [i[0] for k in self.cluster.values() for i in k]
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
            print('DataFrame trim done.')
            self._df=df if save_df else None
        except AttributeError:
            print('Dataframe already trimmed.')

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

    def rename_from_ks_server(self,ks,**kwargs):
        ksdict={i.rep_seq:i.name for i in ks}
        self.rename_from_known(ksdict,**kwargs)

    def rename_from_known(self,knownsequence,method='match',threshold=0.1,scope='cluster',alignscore=None,**kwargs):
        """
        provide KnownSeq object or a string to location of json.
        method can be hybrid_distance,nw_distance,sw_distance,lev_distance
        alignscore is to prevent rename bad alignments.
        """
        if isinstance(knownsequence,str):
            with open(knownsequence,'rt') as f:
                ks = json.load(f)
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
                dis_=poolwrapper(func,alignmentslist,chunks=100,desc='Searching {}'.format(ks[q]),showprogress=True)
                distances.append(dis_)
            min_dis_list = [[i_ for i_,k in enumerate(i) if k<=threshold and k ==min(i)] for i in zip(*distances)]
            for i,j in enumerate(min_dis_list):
                toalias = scope_[i]
                aliasname=''
                if len(j)>1:print('Warning: {} have {} possible alias.'.format(toalias,len(j)))
                for k in j:
                    aliasname += ks[ks_list[k]]
                if aliasname:
                    if alignscore and self.align[toalias].align_score()<alignscore:
                        print('{} alignscore {} < {} cannot alias to {}.'
                            .format(toalias,self.align[toalias].align_score(),alignscore,aliasname))
                        continue
                    if toalias not in old:
                        self.alias.update({toalias:aliasname})
                    else:
                        if self.alias[toalias]!=aliasname:
                            collison.append((toalias,aliasname))
                            print('Collison: {} alias collision {} => {}.'.format(toalias,self.alias[toalias],aliasname))
        new = set(self.alias.keys()) - old
        print('\n Sequence Renamed: ')
        for i in new:
            print(i+ ' => '+self.alias[i])
        if collison: print('Collision found, rename collison manually if needed.')
        return collison

    def rename_joint(self,method='heuristic',alignscore=70,**kwargs):
        """
        rename joint by the already renamed clades (method='heuristic')
        kwargs need to have threshold for align_score threshold to rename an align.
        or rename joint by rename_from_known method (method='match' or 'hybrid_distance'/'sw_distance'/'lev_distance'),
        with scope='align' to include renaming joints.
        """
        if method == 'heuristic':
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
        else:
            knownsequence=kwargs.get('knownsequence',None)
            assert knownsequence, ('Must provide known sequence.')
            self.rename_from_known(knownsequence,method=method,scope='joint',alignscore=alignscore,**kwargs)

    def re_align(self,target,replace=False,**kwargs):
        """
        realign a target node on the tree. with paramethers provided.
        this use the tree_guide_align method. kwargs are align parameters like gap and gapext.
        if replace is Ture, will replace all the children of the node.
        return the alignment object of the target.
        """
        target = self.find(target)[0]
        return self.tree_guide_align(target=target,replace=replace,**kwargs)[target]

    def normalize_df(self):
        """
        normalize percentage of DataFrame
        """
        per=[i for i in self.df.columns if i.endswith('_per')]
        self.df[per]=self.df[per].div(0.01*self.df[per].max(axis=0),axis=1)

    # utility methods
    def __getitem__(self,name):
        """
        get item will return a new object can be treated as alignment or tree clade,
        for use externally to simplify things.
        """
        a=self.align[self.find(name)[0]]
        b=self.tree[self.find(name)[0]]
        return AlignClade(a,b)

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

    def translate(self,seq):
        if isinstance(seq,str):
            return self.alias.get(seq,seq)
        elif isinstance(seq,list):
            return [(self.translate(i[0]),)+i[1:] for i in seq]

    def search(self,query,threshold=5,reverse=False,method='lev_distance',scope='cluster',**kwargs):
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
        dis_=poolwrapper(func,scope__,chunks=100,desc='Searching',showprogress=True)
        for key,score in zip(scope_,dis_):
            if score<=threshold:
                result.append((key,score))
        result = sorted(result,key=lambda x:x[1],reverse=reverse)
        return result

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

    def list_all_rounds(self):
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

    def list_alias(self,contain=''):
        alias = self.alias
        result={}
        for i in set(alias.values()):
            result.update({i:self.find(i)})
        # for k in self.align.keys():
        #     if k[0]!='J' and (k[0] not in 'ACGT') and (k[1] not in 'ACGT'):
        #         if contain in k:
        #             result.append(k)
        return result

    def df_info(self,show=True):
        """
        print the description of dataframe.
        """
        # percentile calculation
        df=self.df.loc[[i.startswith('C') for i in self.df.index],:]
        round_list = df.columns.tolist()
        percentile = []
        for i in round_list:
            percentile.append(np.percentile(df[i][lambda x: x!=0], np.arange(0,120,20)))
        percentile=np.array(percentile).T
        percentile = pd.DataFrame(percentile,index=['Min','20%','40%','60%','80%','Max'],columns=df.columns)
        # unique count, analysis read total read calculation.
        uniquecount = df.apply(lambda x:x!=0).sum()
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
        a[[i for i in round_list if not i.endswith('_per')]]=a[[i for i in round_list if not i.endswith('_per')]].astype(int)
        if show:
            pd.set_option('display.max_columns', None)
            pd.set_option('display.expand_frame_repr', False)
            print(a)
        else:
            return a

    # tools methods
    def compare(self,a,b,format=(1,1,1,0,0),show=True,**kwargs):
        """
        if show;
        align two sequence a and b, print their hybrid distance, and nw distance.
        otherwise return nw alignscore.
        """
        a=self.align[self.find(a)[0]] if isinstance(a,str) else a
        b=self.align[self.find(b)[0]] if isinstance(b,str) else b
        align = a.align(b,**kwargs)
        if show:
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
            print(output)
        else:
            return align.align_score()

    def show_round(self,round='',top=100):
        """
        show the slice of clusters in a round, ranked by percentage.
        """
        _slice=slice(0,top) if isinstance(top,int) else slice(*top)
        countcol=(self.df.loc[[i for i in self.df.index if i.startswith('C')],
                    [round,round+'_per']].sort_values(by=round,ascending=False))
        ccol = countcol.loc[countcol[round]>0,:].iloc[_slice,:]
        ccol['A.K.A']=ccol.index.map(self.translate)
        ccol['Sequence']=ccol.index.map(lambda x:self.align[x].rep_seq())
        ccol.index.name=None
        return ccol

    def round_align(self,target='',round='all',table=None):
        _=self.plot_logo_trend(target=target,rounds=round,plot=False,table=table,save=False)
        return _

    def order_round(self,neworder=[]):
        """
        rearrange round order by providing the new order of rounds.
        """
        assert set(neworder)==set(self.list_all_rounds()),('Must enter all rounds.')
        new = ['sum_count'] +neworder+[i+'_per' for i in neworder]
        self.df = self.df.loc[:,new]

    def call_mutation(self,target:str,seq:(str,Alignment),count=True)->str:
        """
        find mutations in a target compare to a known sequence
        """
        seq = Alignment(seq) if isinstance(seq,str) else seq
        a=seq.align(self[self.find(target)[0]].rep_seq(count).replace('-',''),offset=False)
        mutation=[]
        position=0
        for i,(j,k) in enumerate(zip(*a.seq)):
            if j in 'ACGT': position+=1
            if j!=k:
                m = j+str(position)+k
                mutation.append(m)
        return '/'.join(mutation)

    # method that save txt files

    def info(self,save=False,show=True):
        """
        print basic information about alignment, dataframe, sequence counts, round name, etc.
        """
        if save:
            _save = self.ifexist('INFO_'+save+'.txt' if isinstance(save,str) else 'INFO_{}.txt'.format(self.name))
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
        if save:

            with open(_save,'wt') as f:
                f.write(result)
        if show:
            print(result)

    def describe(self,target=[],format=(1,1,1,0,0),count=True,save=False,show=True):
        """
        print out information of a joint in the tree: include it's parents and children, it's align score and align.
        format is a tuple, id=1, count=1, offset=1, collapse=0, order=0 see Alignment.format()
        count is to change the way rep_seq was calculated.
        """

        target = [target] if isinstance(target,str) else target
        if save:
            _save= 'ALN_'+save+'.txt' if isinstance(save,str) else 'ALN_{}{}.txt'.format(self.translate(target[0]),('_'+str(len(target)-1)+'etc_')*bool(len(target)-1))
            _save=self.ifexist(_save)
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
        if save:
            with open(_save,'wt') as f:
                f.write(output)
        if show:
            print(output)

    def correlation(self,target='',position=[1,2],save=False,show=True):
        """
        show contigency table of 2 positions of a target alignment.
        caution: the index is 1 based, first position is 1
        """
        align = self.align[self.find(target)[0]]
        if save:
            i,j=position
            save = 'CorM_'+save+'.csv' if isinstance(save,str) else 'CorM_'+target+'_N'+str(i)+'_N'+str(j)+'.csv'
            save = self.ifexist(save)
        return align.correlation(position=position,save=save,show=show)

    # method that can generate plots
    def _plot_trend(self,result,title,save):
        ax = result.plot(marker='o', title=title)
        ax.set_xticks(range(len(result)))
        result.index.tolist()
        ax.set_xticklabels(result.index.tolist(), rotation=45)
        plt.tight_layout()
        if save:
            plt.savefig(save)
            plt.clf()
        else:
            plt.show()

    def plot_cluster_trend(self, clade, query='all', plot=True, save=False):
        """
        give an tree element name, find its round percentage trend.
        if query is all, find all round percentage, otherwise find stuff in query.
        """
        if query == 'all':
            query = self.df.columns.tolist()
            query = [i for i in query if i.endswith('per')]
        clade = self.find(clade)[0]
        result = self.df.loc[clade][query]
        result.index = [i[:-4] for i in query]
        result.name=self.translate(clade)
        if save:
            save=self.ifexist('TREND_'+self.translate(result.name)+'.svg')
        if plot:
            self._plot_trend(result,self.translate(clade),save)
        return result

    def plot_compare_cluster_trend(self,clade1,clade2,query='all', plot=True, norm=1,save=False):
        c1=self.plot_cluster_trend(clade1,plot=False)
        c2=self.plot_cluster_trend(clade2,plot=False)
        if save:save=self.ifexist('TREND_'+self.translate(c1.name)+'vs'+self.translate(c2.name)+'.svg')
        ratio=c1/c2
        if norm:
            ratio=ratio/ratio.max()
        if plot:
            self._plot_trend(ratio,self.translate(c1.name)+' / '+self.translate(c2.name),save)
        return ratio

    def plot_pie(self,top=10,condition='sumcount>10',rank='per',scope='cluster',columns=4,plot=True,size=2,save=False,savedf=False,translate=True):
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
        """
        if save:
            _save_= save if isinstance(save,str) else '{}_{}_top{}{}_{}'.format(self.name,condition,top,rank,scope)
            _save_=self.ifexist('PIE_'+_save_+'.svg')
        if savedf:
            _savedf_ = savedf if isinstance(savedf,str) else '{}_{}_top{}{}_{}'.format(self.name,condition,top,rank,scope)
            _savedf_=self.ifexist('TAB_'+_savedf_+'.csv')
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
            fig,axes=plt.subplots(*layout,figsize=figsize)
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
            plt.tight_layout()
            if save:
                plt.savefig(_save_)
                plt.clf()
            else:
                plt.show()
        df = df.loc[align[_slice],:]
        df.loc['Others'] = 100-df.sum()
        if translate:
            df.index=df.index.map(self.translate)
        if savedf:
            temp_index = df.index.tolist()
            df['Sequence']=[self.align.get(x,Alignment('')).rep_seq() for x in temp_index ]
            df.to_csv(_savedf_)
        return df

    def plot_cluster_3d(self,top=10,condition=50,scope='align',rank='per',save=False):
        """
        similar to plot_pie, instead plot on 3d plot.
        """
        if save:
             _save = save if isinstance(save,str) else '{}_{}_top{}'.format(self.name,condition,top)
             _save = self.ifexist('B3D_'+_save+'.svg')
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
        fig = plt.figure(figsize=(8,6))
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
        if save:
           plt.savefig(_save)
           plt.clf()
        else:
           plt.show()

    def _plot_tree(self, node='root',save=False, label='score,seq_count,count', translate=True,size=None,color='count'):
        """
        size: size=(10,10) in inches
        mode : draw use build in draw function, graph use graphviz layout
        label: separate tag with comma. can use 'seq,seq_count,score,count'
        size: auto choose size between 10-30 in height, 10 width. or specify size.
        color: how to label color, methods separated by comma, color = 'count,alias,roundname'
        'count' label based on ranking of total count in all rounds.
        'roundname' label based on count in a certain round.
        'alias' label indicate the alias alignments.
        'None' no labeling.
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

        if save:
            save=self.ifexist(('TREE_'+node+'.svg') if isinstance(save, bool) else 'TREE_'+save+'.svg')
        if node != 'root':
            p = Tree(root=self.tree[self.find(node)[0]], name=self.tree.name+'_'+node,rooted=False)
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

    def plot_tree(self,node='root',condition='',scope='cluster',mode='minimal',**kwargs):
        """
        wrap around _plot_tree method. see it for kwargs usage.
        condition passed to filter_cluster method to filter the clusters to plot.
        if mode is 'minimal', the tree will only contain fitltered clusters (trimmed)
        if mode is 'full', the tree will be every nodes.
        """
        if condition:
            target= self.filter(scope=scope,condition=condition,listonly=True)
            tree=self.sub_tree(target,minimal=(mode=='minimal'))
        else:
            tree = self
        if kwargs.get('save',False):
            save = kwargs.get('save')
            save = ('TREE_'+save) if isinstance(save, str) else 'TREE_{}_{}_{}'.format(node,condition,mode)
            kwargs.update(save=save)

        node = self.tree.common_ancestor(*self.find(node)).name
        tree._plot_tree(node=node,**kwargs)

    def plot_correlation(self,target='',save=False,**kwargs):
        """
        plot correlation matrix of an alignment, using only unique sequences.
        for theils_u, the plot is given x cordinate sequence, predictability of y cordinate.
        plot options in kwargs:
        theil_u=True/False to use theils_u or cramers_v.
        cmap='YlGnBu' for gree - yellow color
        annot = True for annotate correlation numbers
        linewidth = 0.1 for showing the grid line
        figsize = (10,8) for figure size.
        return_results=False return result correlation matrix.
        """
        align = self.align[self.find(target)[0]]
        if save:
            _save = self.ifexist('CorM_'+save+'.svg' if isinstance(save,str) else 'CorM'+target+'.svg')
        else:
            _save=save
        _=align.plot_correlation(save=_save,**kwargs)
        if _:return _

    def plot_logo(self,target='',save=False,count=True):
        """
        plot logo of a specific target.
        """
        if save:
            _save = self.ifexist('LOGO_'+save+'.svg' if isinstance(save,str) else 'LOGO_'+target+'.svg')
        align=self.align[self.find(target)[0]]
        if save:
            align.dna_logo(save=_save,show=False,count=count)
        else:
            align.dna_logo(save=False,show=True,count=count)

    def plot_heatmap(self,top=50,condition='sumcount>10',scope='cluster',order='per',norm=0,contrast=1,labelthre=0.0001,save=False,savedf=False):
        """
        plt heatmap of cluster percentage in all rounds.
        contrast is an interger>=1, for enhancing low percentage sequence.
        order can be 'per'/'??_distance'/'trend' to sort the cluster along y axis based on percentage or distance or trend.
        '??_distance' is the distance method, 'nw_distance'/'hybrid_distance'/'lev_distance'
        if norm = 0, normalize is based on the whole dataframe.
        if norm = 1, normalize along x axis.
        exp: condition='alias,sumcount>0',scope='cluster'
        """
        # check if save location is legit first
        if save:
            _save_= save if isinstance(save,str) else '{}_{}_top{}{}{}'.format(self.name,condition,top,order,'norm'*norm)
            _save_=self.ifexist('HEAT_'+_save_+'.svg')
        if savedf:
            _savedf_ = savedf if isinstance(savedf,str) else '{}_{}_top{}{}{}'.format(self.name,condition,top,order,'norm'*norm)
            _savedf_=self.ifexist('TAB_'+_savedf_+'.csv')
        # preprocess data frame for plotting.
        df = self.plot_pie(top=top,condition=condition,scope=scope,plot=False,translate=False).drop(labels='Others',axis=0)
        if norm:
            df = df.div(df.max(axis=1),axis=0)
        index = df.index.tolist()
        new_index = [index.pop(0)]
        while index:
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
        df = df.loc[new_index]
        correction = 1 if norm else 100
        df_np=np.flip((df.values/correction)**(1/contrast),axis=0)
        rounds = df.columns.tolist()
        cluster = df.index.map(self.translate).tolist()
        fig = plt.figure(figsize=(max(8,round(len(rounds)*0.7)),min(12,max(5,0.4*len(cluster)))))
        gs = gridspec.GridSpec(1,max(9,round(len(rounds)*0.8)),fig)
        ax = fig.add_subplot(gs[0,:-1])
        ax.imshow(df_np,aspect='auto',cmap='YlGnBu')
        # label block value
        if labelthre:
            for i,j in product(range(df_np.shape[0]),range(df_np.shape[1])):
                real_ = df_np[i,j]**contrast
                if real_>labelthre:
                    colo='dimgrey' if df_np[i,j]<0.3 else 'w'
                    ax.text(j, i, '{:.2f}'.format(real_*100),ha="center", va="center", color=colo)
        ax.set_xticks(np.arange(len(rounds)))
        ax.set_yticks(np.arange(len(cluster)))
        ax.set_xticklabels(rounds,rotation=45, ha="right",
                 rotation_mode="anchor")
        cluster.reverse()
        top=len(cluster)
        if len(cluster)<=70:
            ax.set_yticklabels(cluster)
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
        fig.tight_layout()
        if save:
            plt.savefig(_save_)
            plt.clf()
        else:
            plt.show()
        if savedf:
            df['Sequence']=df.index.map(lambda x: self.align[x].rep_seq())
            new= self.df.loc[df.index,:]
            df=pd.concat([df,new],axis=1)
            df.index=df.index.map(self.translate)
            df.to_csv(_savedf_)
        return df

##############################################################################


# sub class of DataReader, specialized for deal with single sequence clusters.

class ClusReader(DataReader):
    """
    for read all sequence in the NGS database that is close to a sequence, and analyse
    light weight tool to quick analyse and cluster sequences on the go.
    """
    @property
    def dr_loc(self):
        return os.path.join(self.working_dir,'raw_data',self.name+'.clusreader')

    @classmethod
    def from_seq(cls,name='UnknownSeq',seq='',dr=None):
        """
        build a simple cluster reader file from list of sequence.
        """

        dr = dr.working_dir if isinstance(dr,DataReader) else dr
        result=cls(name=name,working_dir=dr,save_loc='new_analysis',temp=not dr)
        sequence = seq.split() if isinstance(seq,str) else seq
        input = [{'id':i,'aptamer_seq':j,'sum_per':100/len(sequence),'sum_count':1,name:1} for i,j in enumerate(sequence)]
        result.df=pd.DataFrame(input)
        return result

    @classmethod
    def from_dr(cls,target='',count=2,dis=10,dr=None,table=None):
        """
        query and build cluster reader from NGS database and query target.
        search for sequence with read >= count, lev distance <= dis
        """
        table = table or dr.table_name
        result=cls(name=target,working_dir=dr.working_dir if isinstance(dr,DataReader) else dr,
                        save_loc='new_analysis',temp=not dr)
        target = dr[target].rep_seq().replace('-','') if isinstance(dr,DataReader) else target
        result.table_name=table
        query = """SELECT aptamer_seq from self.table Where sum_count >= {}""".format(count)
        sql=Mysql().connect().set_table(result.table_name)
        sequences = [i['aptamer_seq'] for i in sql.query(query).fetchall()]
        print("Searching {} sequences...".format(len(sequences)))
        distances= mapdistance(target,sequences,dis,showprogress=True)
        selected = [i for i,j in zip(sequences,distances) if j<=dis]
        result.df=sql.search_seq(seq=selected)
        sql.close()
        print("Done. {} matching sequences found.".format(len(selected)))
        return result

    @classmethod
    def from_ngs(cls,name='NewSequence',seq='',count=2,dis=10,table=None,dr=None):
        """
        generate a DataReader file from sequence and NGS table.
        provide a save path to dr or use datareader file's save path if provide as dr.
        need to provide a table or DataReader instance to infer table_name
        """
        table = table or dr.table_name
        table = table if isinstance(table,list) else [table]
        a=0
        for i in table:
            a=cls.from_dr(target=seq,count=count,dis=dis,table=i,dr=dr)+a
        a.name=name
        return a

    @classmethod
    def empty_like(cls,name='new',dr='',table=None):
        table = table or dr.table_name
        result=cls(name=name,working_dir=dr.working_dir if isinstance(dr,DataReader) else dr,
                        save_loc='new_analysis',temp=not dr)
        result.table_name=table
        return result

#################################################

class AlignClade(Alignment,Clade):
    """
    can hold alignment and clade information.
    """
    def __init__(self,*a):
        for b in a:
            for i,j in b.__dict__.items():
                setattr(self,i,j)
