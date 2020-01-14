from RNAstructure import RNA
import ViennaRNA
from collections import defaultdict
from itertools import combinations,product,chain
from functools import partial
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx
from matplotlib.gridspec import GridSpec
from os import path,getcwd,makedirs
import matplotlib as mpl
from matplotlib.text import TextPath
from matplotlib.patches import PathPatch
from matplotlib.font_manager import FontProperties
from MSA import Alignment,IUPAC_decode,poolwrapper
import random
import heapq
import pandas as pd
import NUPACK as NPK

"""
Note:
the algorithms used are from NUPACK, ViennaRNA and RNAstructure.
these programs should be build for specific systems, otherwise it won't work.
"""

pd.options.display.max_colwidth = 500


class lazyproperty():
    """
    lazy property descriptor class.
    """
    def __init__(self,func):
        self.func=func

    def __get__(self,instance,cls):
        if instance is None:
            return self
        else:
            value=self.func(instance)
            setattr(instance,self.func.__name__,value)
            return value


class Structure:
    """
    main class for structure prediction.
    provides 3 different algorithms and compare them.
    """
    def __init__(self,align='',name=None,save_loc=None):
        """
        sequence is stored in Alignment class.
        """
        if align:
            self.align=align if isinstance(align,Alignment) else Alignment(align,name=name)
            self.name=name or self.align.name
        if name:
            self.name=name or self.align.name
        self.foldpara={}
        if save_loc:self.save_loc=save_loc

    def ifexist(self,name):
        """
        for saving files.
        """
        savefolder=getattr(self,"save_loc",getcwd())
        if not path.isdir(savefolder):
            makedirs(savefolder)
        if path.isfile(path.join(savefolder,name)):
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
            return path.join(savefolder,name)

    def __len__(self):
        """
        return sequence length in the Alignment class.
        """
        return len(self.align)

    @lazyproperty
    def seq(self):
        """
        return seuqnce
        """
        return self.align.rep_seq()

    @lazyproperty
    def iupac(self):
        """
        return IPUAC notation of all sequences.
        """
        return self.align.iupac()

    @property
    def seq_length(self):
        """
        counts of how many sequences are there.
        """
        return len(self.seq)
    @property
    def totalsuboptimal(self):
        """
        return how many total suboptimal structures are predicted.
        """
        return len(self._dot)

    @property
    def afterrestrictsuboptimal(self):
        """
        return how many suboptimal structures after restriction is applyed (not include max strucutre limit)
        """
        return len(self.dot)

    @property
    def ratio(self):
        """
        ratio of different structures based on Boltzmann distribution
        """
        energy = np.array(self.energy)
        if len(energy.shape)>1:energy = np.mean(energy,axis=1)
        t=self.foldpara.get('SetTemperature',37)
        t=t+273.15
        kT=8.314*t/4.184e3 # Boltzmann constant * Gas constant then convert kJ to J.
        kT=np.exp(-1/kT)
        if getattr(self,'_pf',None):
            Q=kT**self._pf+1
        else:
            Q=((kT**(energy)).sum())+1
        return kT**(energy)/Q

    @property
    def _ratio(self):
        """
        ratio of different structures based on Boltzmann distribution
        """
        energy = np.array(self._energy)
        if len(energy.shape)>1:energy = np.mean(energy,axis=1)
        # kR=1.380649e-23*8.314/1e3 # Boltzmann constant * Gas constant then convert kJ to J.
        t=self.foldpara.get('SetTemperature',37)
        t=t+273.15
        kT=8.314*t/4.184e3 # Boltzmann constant * Gas constant then convert kJ to J.
        kT=np.exp(-1/kT)
        if getattr(self,'_pf',None):
            Q=kT**self._pf+1
        else:
            Q=((kT**(energy)).sum())+1
        return kT**(energy)/Q

    def print(self,):
        """
        return table in html format
        """
        result={'Predict':[],'Structure':[],'deltaG':[],'Ratio':[],'ED':[]}
        seq=self.align.format(index=True).replace('\n','<br>')
        result['Predict'].append('Seq.')
        result['Structure'].append('##')
        result['deltaG'].append('')
        result['Ratio'].append('')
        result['ED'].append('')
        for i,(d,e,r,ed) in enumerate(zip(self.dot[0:50],self.energy[0:50],self.ratio[0:50],self.ensembledefect[0:50])):
            result['Predict'].append('Pdct '+str(i+1))
            result['Structure'].append(d)
            result['deltaG'].append("{:>3},{:>3},{:>3}".format(*e) if isinstance(e,tuple) else str(e))
            result['Ratio'].append('{:.1f}'.format(r*100))
            result['ED'].append("{:>2},{:>2},{:>2}".format(*ed) if isinstance(ed,tuple) else str(ed))
        df = pd.DataFrame(result)
        result=df.to_html(classes='table',index=False,justify='center',border=0).replace('\\n','<br>')
        result=result.replace('##',seq)
        return result

    def remove(self,toremove):
        """
        ban a list of structures from folded structures.
        """
        nd,ne,np,npt=[],[],[],[]
        for d,e,p,pt in zip(self._dot,self._energy,self._prob,self._pairtuple):
            if d not in toremove:
                nd.append(d)
                ne.append(e)
                np.append(p)
                npt.append(pt)
        self._dot,self._energy,self._prob,self._pairtuple=nd,ne,np,npt

    def subtract(self,b,threshold,method='match',diffthreshold=4):
        """
        remove structures from another structure give a threshold.
        threshold is how many fold the ratio of a give strucutre need to be lower in
        b for i to be delted from self.
        """
        assert len(self)==len(b),('cannot substract different length structures')
        judge = Structure_eq(method,int(diffthreshold))
        toremove=[]
        for d,r in zip(self._dot,self._ratio):
            for d2,r2 in zip(b._dot,b._ratio):
                if judge(d,d2):
                    if r<r2*threshold:
                        print('removed:{}, r1:{} r2:{}'.format(d,r,r2))
                        toremove.append(d)
        self.remove(toremove)

    def fold(self,method='RNAstructure',percent=50,**kwargs):
        """
        method: RNAstructure, ViennaRNA,Compare_RVN
        generate all possible dotbrackets structures
        """
        self.foldpara.update(percent=percent,method=method)
        methods={'RNAstructure':self._RNAstructure_fold,'ViennaRNA':self._ViennaRNA_fold,
            'Compare_RVN':self._compare_method,'Nupack':self._Nupack_fold}
        self._dot,self._energy,self._prob,self._pairtuple,self._ensembledefect=methods[method](percent=percent,**kwargs)
         # total suboptimal is the number before restricted by window size, but it is filtered by single pair.
        # self.restrict_fold(so,p,pt,window,maxstr,method)
        assert len(self._dot)>0,('No structures can be folded under this condition.')
        return self

    def restrict_fold(self,window,cluster='hamming',center='energy',**kwargs):
        """
        restrict fold to certain ones.
        cluster : cluster method, can be
        hamming:hamming distance
        or
        basepair: basepair distance
        or
        tree: tree_edit_distance
        center : the remaining structure selected based on what method: can energy or distance.
        if distance is selected, will use the cluster method for distance calculation.
        """
        self.foldpara.update(window=window)
        so,p,pt,energy,ed=self._dot,self._prob,self._pairtuple,self._energy,self._ensembledefect
        temp = dict(zip(so,zip(p,pt,energy,ed)))
        self.dot=cluster_and_center(list(zip(so,energy)),window,cluster=cluster,center=center)
        self.prob=[temp[i][0] for i in self.dot]
        self.pairtuple = [temp[i][1] for i in self.dot]
        self.energy = [temp[i][2] for i in self.dot]
        self.ensembledefect = [temp[i][3] for i in self.dot]
        return self

    def init_dotgraph(self,maxstr=8,repseq='iupac',**kwargs):
        """
        initialize dotgraph, notate by either Frequency  or IUPAC notation
        default is using IPUAC notation.
        """
        if repseq=='frequency':
            seq=self.seq
        elif repseq=='iupac':
            seq=self.iupac
        else:
            raise ValueError ('Wrong rep sequence code.')

        dot = self.dot[0:int(maxstr)]
        self.dotgraph = [DotGraph(seq,*i,name=f"Predict {k+1}") for k,i in enumerate(zip(dot,self.energy,self.prob,self.pairtuple,self.ensembledefect))]
        return self

    def plot_dot_bracket(self,dotbracket,seq=None,energy=0,**kwargs):
        """
        method to take a single dotbracket structure and sequence to plot its structure.
        will automatically calculate it's predicted energy and other FontProperties
        using ViennaRNA and Nupack if sequence information is provided.
        """
        if seq:
            self.align=Alignment(seq)
        else:
            self.align = Alignment('N'*len(dotbracket))

        # if
        if len(seq)==1 and (set(seq[0])<=set('ATCGU')):
            t=kwargs.get('SetTemperature',37)
            self.foldpara.update(method='ViennaRNA-NUPACK')
            t=t+273.15
            kT=8.314*t/4.184e3 # Boltzmann constant * Gas constant then convert kJ to J.
            kT=np.exp(-1/kT)
            ssd = SingleStructureDesign(seed=seq[0],target=dotbracket)
            seqV,rV,mfeV,eneV,edV = ssd._ViennaRNA_task(seq[0],kT,**kwargs)
            seqN,rN,mfeN,eneN,edN = ssd._Nupack_task(seq[0],kT,**kwargs)
            energy = (round(eneV,1),round(eneN,1))
            ed = "({:.3g},{:.3g})".format(edV,edN)
            self._pf=min(mfeV,mfeN)
        else:
            ed=0

        self._dot=[dotbracket]
        self._energy,self._prob,self._pairtuple,self._ensembledefect=[energy],[[1]*len(dotbracket)],[dotbracket_to_tuple(dotbracket)],[ed]

    def _Nupack_fold(self,percent,**kwargs):
        """
        use nupack algorithm to fold. result is returned in the format
        of tuple of lists in the order of:
        dotbracket structure,energy,probability,pairtuple,ensemble defect.
        """
        self.foldpara.update(kwargs)
        for i in self.align.seq:
            assert set(i)<=set('ATCGU+'), ('Nucleotide code {} is not supported in Nupack Algorithm.'.format(set(i)-set('ATCGU')))

        if len(self.align.seq)==1:
            return self._Nupack_fold_(self.align.seq[0],percent,**kwargs)

        sc=SPT_collector(order=(1,1,0,1))
        for i in self.align.seq:
            sc.fill(i,*self._Nupack_fold_(i,percent,**kwargs))
            print('After {}, total structures = {}'.format(i,len(sc.data)))
        # force save the alifold Algorithm result avoid collison in SPT collector.
        return sc.output()

    def convert_nupack_para(self,**kwargs):
        """
        convert paramters for NUPACK inputs. nupack is using command line inputs.
        """
        dangles=kwargs.get('dangles','some')
        temp=kwargs.get('SetTemperature',37)
        pseudo=kwargs.get('pseudo',False)
        energypara=kwargs.get('energypara','1995')
        backbone=kwargs.get('backbone','rna')
        # multi = True if not pseudo else False
        sodium=kwargs.get('sodium',0.15)
        magnesium=kwargs.get('magnesium',0.002)
        backbone='dna' if backbone=='dna' else backbone+energypara
        para=dict(T=temp,material=backbone,pseudo=pseudo,sodium=sodium,magnesium=magnesium,dangles=dangles,)
        return para

    def _Nupack_fold_(self,sequence,percent,backbone='rna',**kwargs):
        """
        invokes real prediction using nupack.
        give the sequence and return tuple of lists in the order of:
        dotbracket structure,energy,probability,pairtuple,ensemble defect.
        """
        length=len(sequence)
        percent *=0.5**(max(length-50,0)/10)
        sequence=[sequence]
        percent=min(percent,40)
        self.foldpara['percent']=round(percent,1)
        para=self.convert_nupack_para(backbone=backbone,**kwargs)
        self._pf=NPK.pfunc(sequence,**para)
        ss,mfe=NPK.mfe(sequence,**para)[0]
        mfe=float(mfe)
        enerange=abs(mfe)*percent/100
        subopt=NPK.subopt(sequence,enerange,**para)
        prob = NPK.pairs(sequence,cutoff=0.0,**para)
        probdict={(i[0],i[1]):i[2] for i in prob}
        subdot=[i[0] for i in subopt]
        if para.get('pseudo',False):
            subdot=[resolve_pseudoknot(i) for i in subdot]
        subene = [round(float(i[1]),1) for i in subopt]

        pairtuple = [dotbracket_to_tuple(i) for i in subdot]

        prob=[np.array([probdict.get(j,0) for j in i]) for i in pairtuple]

        ed = [ round(NPK.defect(sequence,i)*100) for i in subdot]

        return subdot,subene,prob,pairtuple,ed

    def _ViennaRNA_fold(self,percent,**kwargs):
        """
        use ViennaRNA RNA to fold. same result format as Nupack fold.
        """
        self.foldpara.update(kwargs)
        if len(self.align.seq)==1:
            return self._ViennaRNA_fold_(self.align.seq[0],percent,**kwargs)
        sc=SPT_collector(order=(1,1,0,1))
        for i in self.align.seq:
            sc.fill(i,*self._ViennaRNA_fold_(i,percent,**kwargs))
            print('After {}, total structures = {}'.format(i,len(sc.data)))
        # force save the alifold Algorithm result avoid collison in SPT collector.
        sc.init(*self._ViennaRNA_fold_(self.align.seq,percent,**kwargs))
        return sc.output()

    def _ViennaRNA_fold_(self,sequence,percent,**kwargs):
        """
        use ViennaRNA for prediction.
        """
        length=len(sequence)
        percent *=0.5**(max(length-60,0)/10)
        percent = min(50,percent) # reduce percentage every 15 nt longer
        self.foldpara.update(percent=round(percent,1))
        single=kwargs.get('ForceSingleStranded',None)
        double=kwargs.get('ForceDoubleStranded',None)
        pair=kwargs.get('ForcePair',None)
        temp=kwargs.get('SetTemperature',None)
        # adding constraints
        if temp:
            ViennaRNA.cvar.temperature=temp

        # create fold compound object
        fc = ViennaRNA.fold_compound(sequence)
        if single:
            for i in single:
                fc.hc_add_up(i,ViennaRNA.CONSTRAINT_CONTEXT_ALL_LOOPS)
        if double:
            for i in double:
                fc.hc_add_bp_nonspecific(i,0) # 0 is force it pair with anyone, -1 pair with upstream, 1 pair with downstream.
        if pair:
            for i,j in pair:
                fc.hc_add_bp(i, j, ViennaRNA.CONSTRAINT_CONTEXT_ALL_LOOPS | ViennaRNA.CONSTRAINT_CONTEXT_ENFORCE)

        ss,mfe=fc.mfe()
        mferange=int(abs(mfe)*percent)
        if isinstance(sequence,str):
            subopt=[(i.structure,i.energy) for i in fc.subopt(mferange) if i.structure !=ss]
        else:
            subopt=[]
        subopt = filterlonelypair(subopt)
        subopt += [(ss,mfe)]
         # remove single pairs.
        subopt.sort(key=lambda x:x[1])
        # callculate prob by Boltzmann sampling
        # create model details
        md = ViennaRNA.md()
        # activate unique multibranch loop decomposition
        md.uniq_ML = 1
        fc = ViennaRNA.fold_compound(sequence,md)
        # rescale Boltzmann factors according to MFE
        fc.exp_params_rescale(mfe)
        # compute partition function to fill DP matrices
        _,self._pf=fc.pf()
        # compute ensemble defect.
        ed = [round(fc.ensemble_defect(i[0])*100) for i in subopt]

        ss = list()
        num_samples = 10000
        iterations  = 10
        d  = None # pbacktrack memory object
        for i in range(0, iterations):
            d, i = fc.pbacktrack(num_samples, lambda x,y:y.append(x), ss, d, ViennaRNA.PBACKTRACK_NON_REDUNDANT)
        prob = ensemble_to_prob(ss)
        probs=[prob for i in range(len(subopt))]
        pairtuples = [dotbracket_to_tuple(i[0]) for i in subopt]
        return [i[0] for i in subopt],[round(i[1],1) for i in subopt],probs,pairtuples,ed

    def _RNAstructure_fold(self,percent,**kwargs):
        """
        wrapper to handle aligment multiple sequence.
        """
        self.foldpara.update(kwargs)
        for i in self.align.seq:
            assert set(i)<=set('ATCGU'), ('Nucleotide code {} is not supported in RNAstructure Algorithm.'.format(set(i)-set('ATCGU')))
        if len(self.align.seq)==1:
            return self._RNAstructure_fold_(self.align.seq[0],percent,**kwargs)
        sc=SPT_collector(order=(1,1,0,1))
        for i in self.align.seq:
            sc.fill(i,*self._RNAstructure_fold_(i,percent,**kwargs))
        return sc.output()

    def _RNAstructure_fold_(self,sequence,percent,**kwargs):
        """
        percent:  is the maximum % difference in free energy in suboptimal
        structures from the lowest free energy structure. The default is 20.

        maximumstructures:  is the maximum number of suboptimal structures to
        generate. The default is 20.

        window:  is a parameter that specifies how different the suboptimal
        structures should be from each other (0=no restriction and larger
        integers require structures to be more different). The defaults is 5,
        but this should be customized based on sequence length.
        kwargs is passed to set_foldpara
        wrapper to set parameters for RNAstructure object.
        SetTemperature = 310.15 (default 310.15 K)
        backbone = 'rna' (or 'dna',default is rna)
        ForceDoubleStranded = i (index of nucleotide to be paired)
        ForceFMNCleavage = i (FMN cleavage site, U in GU pair)
        ForceMaximumPairingDistance = distance (maximum distance between paired nt)
        ForceModification = i (chemical modification, this nt will be single strand or end of helix or adjacent to GU pair)
        ForcePair = [(i,j)] (list of pairs to form)
        ForceProhibitPair = [(i,j)] (list of pairs not allowed)
        ForceSingleStranded = i (nt to be single stranded)
        if no parameters passed, remove all constraints.
        """
        backbone=kwargs.pop('backbone','rna')
        p=RNA.fromString(sequence,backbone)
        if kwargs.get('SetTemperature',None):
            kwargs['SetTemperature']+=273.15 # to convert C to K.
        if kwargs:
            for k,i in kwargs.items():
                if ("Force" in k) or ("SetTemp") in k:
                    if isinstance(i,(list,tuple)):
                        for j in i:
                            if isinstance(j,int):
                                getattr(p,k)(j)
                            else:
                                getattr(p,k)(*j)
                    elif isinstance(i,(int,float)):
                        getattr(p,k)(i)
        else:
            p.RemoveConstraints()

        p.PartitionFunction()
        p.FoldSingleStrand(percent=percent,window=0,maximumstructures=10000)
        allstruct=[]
        allenergy=[]
        probs=[]
        pairtuples=[]
        ed = []
        structurenumber=p.GetStructureNumber()
        for i in range(1,structurenumber+1):
            energy = p.GetFreeEnergy(i)
            dotbracket=''
            prob=[]
            pairtuple=[]
            for j in range(1,len(sequence)+1):
                _=p.GetPair(j,i)
                prob.append(p.GetPairProbability(j,_))
                pairtuple.append((j,_))
                if _ ==0:
                    dotbracket+='.'
                elif _>j:
                    dotbracket+='('
                else:
                    dotbracket+=')'
            pairtuples.append(pairtuple)
            allstruct.append(dotbracket)
            allenergy.append(energy)
            ed.append(round(p.GetEnsembleDefect(i)/len(sequence)*100))
            probs.append(np.nan_to_num(np.array(prob)))
        return allstruct,allenergy,probs,pairtuples,ed

    def _compare_method(self,percent,**kwargs):
        """
        get the collection of all possible structures predicted by 3 different algorithms.
        use average energy to rank the suboptimal structures.
        """
        soV,eV,pV,ptV,edV=self._ViennaRNA_fold(percent,**kwargs)
        soR,eR,pR,ptR,edR=self._RNAstructure_fold(percent,**kwargs)
        soN,eN,pN,ptN,edN=self._Nupack_fold(percent,**kwargs)
        comS=set(soV+soR+soN)
        setV=dict(zip(soV,zip(eV,pV,ptV,edV)))
        setR=dict(zip(soR,zip(eR,pR,ptR,edR)))
        setN=dict(zip(soN,zip(eN,pN,ptN,edN)))
        so_c = list(comS)
        e_c,p_c,pt_c,ed_c=[],[],[],[]
        for i in so_c:
            holder=[]
            for j in range(4):
                holder.append((setR.get(i,[0,0,0,0])[j],setV.get(i,[0,0,0,0])[j],setN.get(i,[0,0,0,0])[j]))
            e_c.append(holder[0])
            p_c.append(np.mean(holder[1],axis=0))
            pt_c.append(max(holder[2],key=bool))
            ed_c.append(holder[3])
        return so_c,e_c,p_c,pt_c,ed_c

    def plot_fold(self,maxcol=100,save=False,showpara=True,**kwargs):
        """
        generate plot of the dotgraph.
        """
        strutno=len(self.dotgraph)
        plot_size =max(self.dotgraph[0].plot_size())/200*4.5 # this is estimating size of each panel
        plot_size=max(plot_size,4)
        panels=panel_count(strutno+showpara,maxcol)
        figwidth,figheight=(max(plot_size*panels[1],8),max(plot_size*panels[0],8))
        fig = plt.figure(figsize=(figwidth,figheight))
        # fig,axes = plt.subplots(*panels,figsize=(max(6*panels[1],8),max(6*panels[0],8)))
        method=self.foldpara.get('method',None)
        N=self.totalsuboptimal
        M = self.afterrestrictsuboptimal
        if method=='Compare_RV': method='RNAstructure + ViennaRNA'
        fig.suptitle(f'{self.name} {method} => {M}/{N}',family='fantasy',fontsize=20,weight='bold')

        cbgs=GridSpec(1,1,left=0.5-2/figwidth,right=0.5+2/figwidth,top=0.01+0.1/figheight,bottom=0.01)
        cbax=fig.add_subplot(cbgs[0])
        gradient = np.linspace(0, 1, 256)
        gradient = np.vstack((gradient,gradient))
        color=kwargs.get('basepair_kwargs',{}).get('color','cool')
        maxprob=np.max(self.prob)
        cbax.imshow(gradient,aspect='auto',cmap=plt.get_cmap(color))
        cbax.set_xlim(-85,256+85)
        cbax.set_ylim(0,2)
        cbax.set_aspect('auto')
        cbax.text(-20,0.2,'0',fontsize=12)
        cbax.text(259,0.2,"{:.2f}".format(maxprob),fontsize=12)
        cbax.set_axis_off()
        cbax.set_title('Base pair probability')
        ploggs = GridSpec(*panels,left=0.05,right=0.95,top=0.99-1.3/figheight,bottom=0.01+0.25/figheight)
        axes=[]
        for c,(i,j) in zip(range(strutno+1),product(range(panels[0]),range(panels[1]))):
            axes.append(fig.add_subplot(ploggs[i,j]))

        for ax,dotgrap in zip(axes,self.dotgraph):
            dotgrap.plot_2d(ax=ax,maxprob=maxprob,**kwargs)

        # add prediction parameters to next axes
        if showpara:
            ax=axes[-1]
            ax.set_axis_off()
            text="Folding Parameter:\n"+'\n'.join(["{} : {}".format(k,str(i)) for k,i in self.foldpara.items()])
            ax.text(0.01,0.85,text, transform=ax.transAxes, fontsize=max(int(2*plot_size),6),verticalalignment='top',family='monospace')
        if save:
            plotbackend=kwargs.get('plotbackend','.png')
            save = save if isinstance(save,str) else '2DP_'+self.name
            save = self.ifexist(save+plotbackend)
            plt.savefig(save,dpi=150)
        else:
            plt.show()
        return figheight,figwidth


class Multistrand(Structure):
    """
    sub-class to handle co-fold:
    folding of multiple structures.
    give the predicted complex concentrations and their optimal structures.
    only use Nupack algorithm.
    """
    def __init__(self,strands=[],conc=[]):
        self.strands=strands
        self.conc=conc

    def fold(self,**kwargs):
        """
        use nupack complexes function to fold complexes.
        """
        para=self.convert_nupack_para(**kwargs)
        para.update(maxcofoldstrand=kwargs.get('maxcofoldstrand',2))
        result=NPK.complexes(self.strands,self.conc,**para)
        data1={i:j[-2:] for i,j in result.items()}
        df1=pd.DataFrame.from_dict(data1,orient='index',columns=['Structure','deltaG'])
        data2={i:j[:-2] for i,j in result.items()}
        df2=pd.DataFrame.from_dict(data2,orient='index',columns=['Strands','Q(kcal/mol)','Conc.(M)']).sort_values(by='Conc.(M)',ascending=False)
        df1=df1.loc[df2.index,:]
        df1['deltaG']=df1['deltaG'].map('{:.1f}'.format)
        df2['Q(kcal/mol)']=df2['Q(kcal/mol)'].map('{:.1f}'.format)
        df2['Conc.(M)']=df2['Conc.(M)'].map('{:.3e}'.format)
        self.structure_df=df1
        self.complex_df=df2

    def to_html(self,df='structure_df'):
        result=getattr(self,df).to_html(classes='table',index=True,justify='center',border=0)#.replace('\\n','<br>')
        return result

class MutableSequence():
    """
    class to generate mutations given a IPUAC notated seed and target
    structure. will try to put base pairs or wobble pairs at pairing sites.
    """
    def __init__(self,seed,target=None):
        self.seed=seed
        self.target=target or '.'*len(self.seed)
        assert len(self.seed)==len(self.target) , ('Seed and target must be same length.')

        self.pairtuple=dotbracket_to_tuple(self.target.replace('*','.'))

    @lazyproperty
    def totalmutation(self):
        count=[]
        s=self.seq_table
        for i in self.seq_table:
            if isinstance(i[0],int):
                count.append((s[i[0]].count('T')+s[i[0]].count('G'))/len(s[i[0]])+1)
            else:
                count.append(len(i))
        return int(np.prod(count))

    @lazyproperty
    def seq_table(self):
        seq=list(map(list,map(IUPAC_decode,self.seed)))
        for i,j in enumerate(self.pairtuple):
            if 0<j[1]<j[0] and (len(seq[j[0]-1])+len(seq[j[1]-1])>2):
                if len(seq[j[1]-1])>len(seq[j[0]-1]):
                    seq[j[0]-1]=[j[1]-1]
                else:
                    seq[j[1]-1]=[j[0]-1]
        return seq

    def mut_iterator(self,n):
        if n > 0.5*self.totalmutation:
            for a in product(*self.seq_table):
                yield from self.concate(a)
        else:
            yield from self.randomsampler(n)

    def randomsampler(self,n):
        result = set()
        # count=0
        while len(result)<n:
            new=list(map(random.choice,self.seq_table))
            for k,i in enumerate(new):
                if isinstance(i,int):
                    new[k]=random.choice(self.revcom(new[i]))
            key=''.join(new)
            if key not in result:
                result.add(key)
                yield key

    def concate(self,a):
        a=list(a)
        for k,i in enumerate(a):
            if isinstance(i,int):
                a[k]=self.revcom(a[i])
        for _ in product(*a):
            yield ''.join(_)

    def revcom(self,i):
        c=dict(zip('ATCG','TAGC'))
        c['T']+='G'
        c['G']+='T'
        return c[i]


class SingleStructureDesign(MutableSequence):
    """
    class to design single strand structure using different algorithms.
    """
    def __init__(self,seed,target,**kwargs):
        super().__init__(seed,target)
        # self.foldpara={}

    def generate(self,method,top=50,n=10000,**kwargs):
        """
        generate random sequence
        """
        # self.foldpara=kwargs
        methods={'ViennaRNA':self._generate_Vienna,'RNAstructure':self._generate_RNAstructure,'Nupack':self._generate_Nupack}
        if method not in methods.keys():
            raise KeyError ('{} not in supported single strand design Algorithm'.format(method))
        result=methods[method](n,top,**kwargs)
        # result=sorted(result,key=lambda x:(-x[1],x[3]))
        self.result=result
        result=dict(zip(['Predict','Sequence','Ratio','MFE','TgtdG','ED'],[list(range(1,1+len(result)))]+list(zip(*result))))
        df=pd.DataFrame(result).loc[:,['Predict','Sequence','TgtdG','MFE','Ratio','ED']]
        df['TgtdG']=df['TgtdG'].map('{:.1f}'.format)
        df['MFE']=df['MFE'].map('{:.1f}'.format)
        df['Ratio']=df['Ratio'].map(partial(round,ndigits=1))
        df['Predict']=df['Predict'].map('Predict {:>2}'.format)
        df['ED']=df['ED'].map(lambda x:round(x*100))
        self.df=df
        return df

    def to_html(self):
        result=self.df.to_html(classes='table',index=False,justify='center',border=0)#.replace('\\n','<br>')
        return result

    def _generate_Nupack(self,n,top,**kwargs):

        if "*" in self.target:
            raise ValueError('* not allowed in Nupack.')
        total = min(50,int(top/2))
        task=partial(NPK.design,sequence=self.seed,structure=self.target,**kwargs)
        sequences = poolwrapper(task,list(range(total)),total=total,showprogress=True,desc='NUPACK Design')
        t=kwargs.get('SetTemperature',37)
        kT=8.314*(t+273.15)/4.184e3 # Boltzmann constant * Gas constant then convert kJ to J.
        kT=np.exp(-1/kT)
        task2 = partial(self._Nupack_task,kT=kT)
        tempresult = poolwrapper(task2,sequences,total=total,showprogress=True,desc='NUPACK Evaluate')
        result=Design_collector(top,lambda x:(x[1],-x[4],-x[3]))
        for i in tempresult:
            result.add(i)
        return result.collect()

    def _generate_Vienna(self,n,top,SetTemperature=37,**kwargs):
        if '*' in self.target:
            return self._generate_RNAstructure(n,top,SetTemperature=SetTemperature,_rnastru=False,**kwargs)
        else:
            t=SetTemperature#self.foldpara.get('SetTemperature',37)
            ViennaRNA.cvar.temperature=t
            t=t+273.15
            kT=8.314*t/4.184e3 # Boltzmann constant * Gas constant then convert kJ to J.
            kT=np.exp(-1/kT)
            result=Design_collector(top,lambda x:(x[1],-x[4],-x[3]))
            task = partial(self._ViennaRNA_task,kT=kT)
            total = self.totalmutation if n > 0.5*self.totalmutation else n
            tempresult = poolwrapper(task,self.mut_iterator(n),total=total,showprogress=True)
            for i in tempresult:
                result.add(i)
        return result.collect()

    def _ViennaRNA_task(self,seq,kT,**kwargs):
        fc=ViennaRNA.fold_compound(seq)
        _,gfe = fc.pf()
        _,mfe=fc.mfe()
        ed=fc.ensemble_defect(self.target)
        ene=fc.eval_structure(self.target)
        r = kT**ene/kT**gfe*100
        return (seq,r,mfe,ene,ed)

    def _Nupack_task(self,seq,kT,**kwargs):
        sequence=[seq]
        backbone=kwargs.get('backbone','rna')
        dangles=kwargs.get('dangles','some')
        temp=kwargs.get('SetTemperature',37)
        pseudo=kwargs.get('pseudo',False)
        sodium=kwargs.get('sodium',0.15)
        magnesium=kwargs.get('magnesium',0.002)
        para=dict(T=temp,material=backbone,pseudo=pseudo,sodium=sodium,magnesium=magnesium,dangles=dangles)
        gfe=NPK.pfunc(sequence,**para)
        ss,mfe=NPK.mfe(sequence,**para)[0]
        mfe=float(mfe)
        ene=NPK.energy(sequence,self.target,**para)
        ed = NPK.defect(sequence,self.target,**para)
        r = kT**ene/kT**gfe*100

        return (seq,r,mfe,ene,ed)

    def _generate_RNAstructure(self,n,top,SetTemperature=37,_rnastru=True,**kwargs):
        """
        multiprocessing version.
        """
        if '*' in self.target:
            judge = Structure_eq('starmatch')
        else:
            judge = Structure_eq(kwargs.get('strexc_method','match'),kwargs.get('strexc_threshold',None))
        foldmethod = Structure()._RNAstructure_fold_ if _rnastru else Structure()._ViennaRNA_fold_
        result=Design_collector(top,lambda x:(-x[3],-x[4],x[1]))
        temp=SetTemperature#self.foldpara.get('SetTemperature',37)
        t=temp+273.15
        kT=8.314*t/4.184e3
        kT=np.exp(-1/kT)
        total = self.totalmutation if n > 0.5*self.totalmutation else n
        task=partial(self._RNAstructure_task,judge=judge,foldmethod=foldmethod,percent=int(kwargs.get('percent',50)),temp=temp,kT=kT)
        tempresult = poolwrapper(task,self.mut_iterator(n),total=total,showprogress=True)
        for i in tempresult:
            result.add(i)

        return result.collect()

    def _RNAstructure_task(self,seq,judge,foldmethod,percent,temp,kT,**kwargs):
        """
        multiprocessing task.
        """

        s,e,*_,ed = foldmethod(sequence=seq,percent=percent,SetTemperature=temp)
        e=np.array(e)
        totalR = (kT**(e)).sum()
        mfe=np.min(e)
        ene_=[]
        r_=[]
        ed_=[]
        for si,ene,edi in zip(s,e,ed):
            if judge(self.target,si):
                ene_.append(ene)
                r_.append(kT**ene/totalR)
                ed_.append(edi)
        if r_:
            return (seq, sum(r_)*100 ,mfe,min(ene_),np.mean(ed_))
        else:
            return None


class MultiStructureDesign(SingleStructureDesign):
    def generate(self,method='Nupack',top=10,**kwargs):
        assert method=='Nupack',("\"{}\" is not supported. Only Nupack is supported.".format(method))
        return SingleStructureDesign.generate(self,method,top=top,**kwargs)

class StructurePerturbation(SingleStructureDesign):
    def __init__(self,seed,target,n,mutrange=None,**kwargs):
        self.seq=seed
        self.target=target
        self.n=n
        assert len(seed)==len(target), ('Sequence and Structure must be of same length.')
        totmut = list(range(len(seed)))
        if mutrange is None:
            self.mutable = totmut
        else:
            self.mutable=[]
            for i in totmut:
                for k,j in mutrange:
                    if k>j: k,j=j,k
                    if k<=i<=j:
                        self.mutable.append(i)
        assert n<=len(self.mutable), ('Total mutation sites must less than allowed mutable region.')

    @lazyproperty
    def totalmutation(self):
        n = len(self.mutable)
        m=self.n
        c = 4**self.n
        p = np.prod(range(n-m+1,n+1))/np.prod(range(1,m+1))
        return int(p*c)

    def mut_iterator(self,maxinteration):
        if maxinteration>0.5*self.totalmutation:
            for i in combinations(self.mutable,self.n):
                seq=[[s] if k not in i else ['A','T','C','G'] for k,s in enumerate(self.seq)]
                for l in product(*seq):
                    yield ''.join(l)
        else:
            yield from self.randomsampler(maxinteration)

    def randomsampler(self,maxiter):
        result=set()
        while len(result)<maxiter:
            tomut = random.sample(self.mutable,self.n)
            seq=[[s] if k not in tomut else ['A','T','C','G'] for k,s in enumerate(self.seq)]
            new=list(map(random.choice,seq))
            key=''.join(new)
            if key not in result:
                result.add(key)
                yield key

    def generate(self,iteration,goal='inhibit',SetTemperature=37,**kwargs):
        methods={'ViennaRNA':self._ViennaRNA_task,'Nupack':self._Nupack_task}
        func= methods.get(kwargs['method'],False)
        if not func: raise KeyError('{} not supported for structure perturbation'.format(kwargs['method']))

        t=SetTemperature#self.foldpara.get('SetTemperature',37)
        ViennaRNA.cvar.temperature=t
        t=t+273.15
        kT=8.314*t/4.184e3 # Boltzmann constant * Gas constant then convert kJ to J.
        kT=np.exp(-1/kT)
        if goal=='inhibit':
            sorter = lambda x:(-x[1],x[3],x[4],) # order is 1: ratio,2: mfe, 3:ene, 4:ED
        else:
            sorter = lambda x:(x[1],-x[4],-x[3])
        result=Design_collector(50,sorter)

        task = partial(func,kT=kT,**kwargs) # return (seq,ratio, mfe, energy)
        total = self.totalmutation if iteration > 0.5*self.totalmutation else iteration
        tempresult = poolwrapper(task,self.mut_iterator(iteration),total=total,showprogress=True)
        for i in tempresult:
            result.add(i)
        self.result=result.collect()
        original = func(self.seq,kT,**kwargs)
        result = [original] + self.result
        result=dict(zip(['Predict','Sequence','Ratio','MFE','TgtdG','ED'],[list(range(len(result)))]+list(zip(*result))))
        df=pd.DataFrame(result).loc[:,['Predict','Sequence','TgtdG','MFE','Ratio','ED']]
        df['TgtdG']=df['TgtdG'].map('{:.1f}'.format)
        df['MFE']=df['MFE'].map('{:.1f}'.format)
        df['Ratio']=df['Ratio'].map(partial(round,ndigits=1))
        df['Predict']=df['Predict'].map('Predict {:>2}'.format)
        df['ED']=df['ED'].map(lambda x:round(x*100))
        df.iloc[0,0]='Original'
        self.df=df
        return df

class DotGraphConstructor:
    """
    base class for construction of dotgraph.
    """
    def from_tuples(self,tuples):
        """
        Create a bulge_graph from a list of pair tuples. Unpaired
        nucleotides have a pairing partner of 0.
        """
        stems = []
        bulges = []

        tuples.sort()  # We move along the backbone
        tuples = iter(tuples)
        (t1, t2) = next(tuples)

        prev_from = t1
        prev_to = t2

        start_from = prev_from
        start_to = prev_to
        last_paired = prev_from

        for t1, t2 in tuples:
            (from_bp, to_bp) = (t1, t2)

            if abs(to_bp - prev_to) == 1 and prev_to != 0:  # adjacent basepairs on 3' strand
                # stem
                if (((prev_to - prev_from > 0 and to_bp - from_bp > 0) or
                     (prev_to - prev_from < 0 and to_bp - from_bp < 0)) and
                        (to_bp - prev_to) == -(from_bp - prev_from)):
                    (prev_from, prev_to) = (from_bp, to_bp)
                    last_paired = from_bp
                    continue

            if to_bp == 0 and prev_to == 0:
                # bulge
                (prev_from, prev_to) = (from_bp, to_bp)
                continue
            else:
                if prev_to != 0:
                    new_stem = tuple(sorted([tuple(sorted([start_from - 1, start_to - 1])),
                                             tuple(sorted([prev_from - 1, prev_to - 1]))]))
                    if new_stem not in stems:
                        stems += [new_stem]

                    last_paired = from_bp
                    start_from = from_bp
                    start_to = to_bp
                else:
                    new_bulge = ((last_paired - 1, prev_from - 1))
                    bulges += [new_bulge]

                    start_from = from_bp
                    start_to = to_bp

            prev_from = from_bp
            prev_to = to_bp
        # Take care of the last element
        if prev_to != 0:
            new_stem = tuple(sorted([tuple(sorted([start_from - 1, start_to - 1])),
                                     tuple(sorted([prev_from - 1, prev_to - 1]))]))
            if new_stem not in stems:
                stems += [new_stem]
        if prev_to == 0:
            new_bulge = ((last_paired - 1, prev_from - 1))
            bulges += [new_bulge]

        self.from_stems_and_bulges(stems, bulges)

    def from_stems_and_bulges(self,stems,bulges):
        """
        Create the graph from the list of stems and bulges.

        :param stems: A list of tuples of two two-tuples, each containing the start
                      and end nucleotides of each strand of the stem.
        :param bulges: A list of tuples containing the starts and ends of the
                       of the bulge regions.
        :return: Nothing, just make the bulgegraph
        """
        assert self.defines == {}
        assert self.edges == defaultdict(set)
        for i in range(len(stems)):
            # one is added to each coordinate to make up for the fact that residues are 1-based
            ss1 = stems[i][0][0] + 1
            ss2 = stems[i][0][1] + 1
            se1 = stems[i][1][0] + 1
            se2 = stems[i][1][1] + 1

            self.defines['y%d' % (i)] = [min(ss1, se1), max(ss1, se1),
                                         min(ss2, se2), max(ss2, se2)]
            self.weights['y%d' % (i)] = 1

        for i in range(len(bulges)):
            bulge = bulges[i]
            self.defines['b%d' % (i)] = sorted([bulge[0] + 1, bulge[1] + 1])
            self.weights['b%d' % (i)] = 1


        self.create_bulge_graph(stems, bulges)

        self.create_stem_graph(stems, len(bulges))

        self.collapse()

        self.sort_defines()

        self.relabel_nodes()

        self.remove_degenerate_nodes()

    def create_bulge_graph(self,stems,bulges):
        """
        Find out which stems connect to which bulges

        Stems and bulges which share a nucleotide are considered connected.

        :param stems: A list of tuples of tuples of the form [((s1, e1), (s2, e2))]
                      where s1 and e1 are the nucleotides at one end of the stem
                      and s2 and e2 are the nucleotides at the other.

        :param bulges: A list of tuples of the form [(s, e)] where s and e are the
                       numbers of the nucleotides at the start and end of the bulge.
        """
        for i in range(len(stems)):
            stem = stems[i]
            for j in range(len(bulges)):
                bulge = bulges[j]
                if any_difference_of_one(stem, bulge):
                    self.edges['y{}'.format(i)].add('b{}'.format(j))
                    self.edges['b{}'.format(j)].add('y{}'.format(i))

    def create_stem_graph(self,stems,bulge_counter):
        """
        Determine which stems are connected to each other. A stem can be connected to
        another stem when there is an interior loop with an unpaired nucleotide on
        one side. In this case, a bulge will be created on the other side, but it
        will only consist of the two paired bases around where the unpaired base
        would be if it existed.

        The defines for these bulges will be printed as well as the connection strings
        for the stems they are connected to.

        :param stems: A list of tuples of tuples of the form [((s1, e1), (s2, e2))]
                      where s1 and e1 are the nucleotides at one end of the stem
                      and s2 and e2 are the nucleotides at the other.
        :param bulge_counter: The number of bulges that have been encountered so far.

        :returns: None
        """
        # print "stems:", stems
        for i, j in combinations(range(len(stems)), 2):
            for k1, k2, l1, l2 in product(range(2), repeat=4):
                s1 = stems[i][k1][l1]
                s2 = stems[j][k2][l2]
                if k1 == 1 and stems[i][0][l1] == stems[i][1][l1]:
                    continue
                if k2 == 1 and stems[j][0][l2] == stems[j][1][l2]:
                    continue
                if abs(s1 - s2) == 1:
                    bn = 'b{}'.format(bulge_counter)
                    # self.defines[bn] = [min(s1, s2)+1, max(s1, s2)+1]
                    self.defines[bn] = []
                    self.weights[bn] = 1

                    self.edges['y{}'.format(i)].add(bn)
                    self.edges[bn].add('y{}'.format(i))

                    self.edges['y{}'.format(j)].add(bn)
                    self.edges[bn].add('y{}'.format(j))

                    bulge_counter += 1

    def collapse(self):
        """
        If any vertices form a loop, then they are either a bulge region or
        a fork region. The bulge (interior loop) regions will be condensed
        into one node.
        """
        new_vertex = True
        while new_vertex:
            new_vertex = False
            bulges = [k for k in self.defines if k[0] != 'y']

            for (b1, b2) in combinations(bulges, r=2):
                if self.edges[b1] == self.edges[b2] and len(self.edges[b1]) == 2:
                    connections = self.connections(b1)

                    all_connections = [sorted((self._get_sides_plus(connections[0], b1)[0],
                                               self._get_sides_plus(connections[0], b2)[0])),
                                       sorted((self._get_sides_plus(connections[1], b1)[0],
                                               self._get_sides_plus(connections[1], b2)[0]))]
                    # print(all_connections)
                    if all_connections == [[1, 2], [0, 3]]:
                        # interior loop

                        self.merge_vertices([b1, b2])

                        new_vertex = True
                        break
        # print(self.edges)

    def sort_defines(self):
        """
        Sort the defines of interior loops and stems so that the 5' region
        is always first.
        """
        for k in self.defines.keys():
            d = self.defines[k]

            if len(d) == 4:
                if d[0] > d[2]:
                    new_d = [d[2], d[3], d[0], d[1]]
                    self.defines[k] = new_d

    def relabel_nodes(self):
        """
        Change the labels of the nodes to be more indicative of their nature.

        s: stem
        h: hairpin
        i: interior loop
        m: multiloop
        f: five-prime unpaired
        t: three-prime unpaired
        """
        stems = []
        hairpins = []
        interior_loops = []
        multiloops = []
        fiveprimes = []
        threeprimes = []

        seq_length = 0
        for d in self.defines:
            for r in self.define_range_iterator(d):
                seq_length += r[1] - r[0] + 1

        for d in self.defines.keys():
            if d[0] == 'y' or d[0] == 's':
                stems += [d]
                continue

            if len(self.defines[d]) == 0 and len(self.edges[d]) == 1:
                hairpins += [d]
                continue

            if len(self.defines[d]) == 0 and len(self.edges[d]) == 2:
                multiloops += [d]
                continue

            if len(self.edges[d]) <= 1 and self.defines[d][0] == 1:
                fiveprimes += [d]
                continue

            if len(self.edges[d]) == 1 and self.defines[d][1] == seq_length:
                threeprimes += [d]
                continue

            if (len(self.edges[d]) == 1 and
                self.defines[d][0] != 1 and
                    self.defines[d][1] != seq_length):
                hairpins += [d]
                continue

            if d[0] == 'm' or (d[0] != 'i' and len(self.edges[d]) == 2 and
                                       self.weights[d] == 1 and
                                       self.defines[d][0] != 1 and
                                       self.defines[d][1] != seq_length):
                multiloops += [d]
                continue

            if d[0] == 'i' or self.weights[d] == 2:
                interior_loops += [d]

        stems.sort(key=self.compare_stems)
        hairpins.sort(key=self.compare_hairpins)
        multiloops.sort(key=self.compare_bulges)
        interior_loops.sort(key=self.compare_stems)

        if fiveprimes:
            d, = fiveprimes
            relabel_node(self, d, 'f0')
        if threeprimes:
            d, = threeprimes
            relabel_node(self, d, 't0')
        for i, d in enumerate(stems):
            relabel_node(self, d, 's%d' % (i+1))
        for i, d in enumerate(interior_loops):
            relabel_node(self, d, 'i%d' % (i+1))
        for i, d in enumerate(multiloops):
            relabel_node(self, d, 'm%d' % (i+1))
        for i, d in enumerate(hairpins):
            relabel_node(self, d, 'h%d' % (i+1))

    def compare_stems(self, b):
        """
        A function that can be passed in as the key to a sort.
        """
        return (self.defines[b][0], 0)

    def compare_bulges(self, b):
        """
        A function that can be passed in as the key to a sort.

        Compares based on the nucleotide number
        (using define_a to allow for sorting 0-length MLs)
        """
        return self.define_a(b)

    def compare_hairpins(self, b):
        connections = self.connections(b)
        return (self.defines[connections[0]][1], 1e10)

    def remove_degenerate_nodes(self):
        """
        For now just remove all hairpins that have no length.
        """
        to_remove = []
        for d in self.defines:
            if d[0] == 'h' and len(self.defines[d]) == 0:
                to_remove += [d]

        for r in to_remove:
            remove_vertex(self, r)

    def connections(self,bulge):
        """
        :param g: Graph-like: A BulgeGraph or BulgeGraphConstruction.
        """
        def sort_key(x):
            if self.defines[x] and self.defines[x][0] == 1:
                # special case for stems at the beginning since there is no
                # adjacent nucleotide 0
                return 0
            return self.define_a(x)[0]
        connections = list(self.edges[bulge])
        connections.sort(key=sort_key)
        return connections

    def _get_sides_plus(self,s1,bulge):
        """
        Get the side of s1 that is next to b.

        s1e -> s1b -> b

        :param s1: The stem.
        :param b: The bulge.
        :return: A tuple indicating the corner of the stem that connects
                 to the bulge as well as the corner of the bulge that connects
                 to the stem.
                 These sides are equivalent to the indices of the define.
        """
        if bulge not in self.edges[s1]:
            raise ValueError(
                "_get_sides_plus expects stem to be connected to bulge!")

        s1d = self.defines[s1]
        bd = self.defines[bulge]  # pylint: disable=C0103

        if not bd:
            bd = self._define_a_zerolength(bulge)  # pylint: disable=C0103
            bd[0] += 1
            bd[1] -= 1

        # before the stem on the 5' strand
        if s1d[0] - bd[1] == 1:
            return (0, 1)
        # after the stem on the 5' strand
        if bd[0] - s1d[1] == 1:
            return (1, 0)
        # before the stem on the 3' strand
        if s1d[2] - bd[1] == 1:
            return (2, 1)
        # after the stem on the 3' strand
        if bd[0] - s1d[3] == 1:
            return (3, 0)

        raise KeyError(
            "Faulty bulge {}:{} connected to {}:{}".format(bulge, bd, s1, s1d))

    def _define_a_zerolength(self, elem):  # TODO speed-up by caching
        """
        Return the define with adjacent nucleotides for a zero-length element.

        Hereby we define that in cases of ambiuigity, the alphabetically first
        zero-length element comes at the lowest nucleotide position etc.

        :param elem: An element, e.g. "m0
        """
        if self.defines[elem] != []:
            raise ValueError("{} does not have zero length".format(elem))
        edges = self.edges[elem]
        if len(edges) == 1:  # Hairpin
            stem, = edges
            define = self.defines[stem]
            if define[2] == define[1] + 1:
                return [define[1], define[2]]
            raise KeyError("Very strange zero-length hairpin {} "
                                      "(not?) connected to {}".format(elem, stem))
        if len(edges) == 2:
            stem1, stem2 = edges
            # See if this is the only element connecting the two stems.
            connections = self.edges[stem1] & self.edges[stem2]
            zl_connections = []
            for conn in connections:
                if self.defines[conn] == []:
                    zl_connections.append(conn)
            assert elem in zl_connections
            # We DEFINE the 0-length connections to be sorted alphabetically by position
            zl_connections.sort()

            zl_coordinates = self._zerolen_defines_a_between(stem1, stem2)
            if len(zl_connections) != len(zl_coordinates):
                raise ValueError("Expecting stems {} and {} to have {} zero-length "
                                          "connections at nucleotide positions {}, however, "
                                          "found {} elements: {}".format(stem1, stem2,
                                                                         len(zl_coordinates),
                                                                         zl_coordinates,
                                                                         len(zl_connections),
                                                                         zl_connections))
            zl_coordinates = list(zl_coordinates)
            zl_coordinates.sort()
            i = zl_connections.index(elem)
            return list(zl_coordinates[i])
        raise ValueError("Very strange zero length bulge {} with more than 2 adjacent "
                                  "elements: {}.".format(elem, edges))

    def _zerolen_defines_a_between(self, stem1, stem2):
      zl_coordinates = set()
      for k, l in product(range(4), repeat=2): # pylint: disable=W1638
          if abs(self.defines[stem1][k] - self.defines[stem2][l]) == 1:
              d = [self.defines[stem1][k], self.defines[stem2][l]]
              d.sort()
              zl_coordinates.add(tuple(d))
      return zl_coordinates

    def get_vertex(self, name=None):
      """
      Return a new unique vertex name starting with `x`.

      At this stage stems and bulges are not distinguished
      """

      if name is None:
          name = "x{}".format(self._name_counter)
          self._name_counter += 1

      return name

    def merge_vertices(self,vertices):
        """
        This is done when two of the outgoing strands of a stem
        go to different bulges
        It is assumed that the two ends are on the same sides because
        at least one vertex has a weight of 2, implying that it accounts
        for all of the edges going out of one side of the stem

        :param vertices: A list of vertex names to combine into one.
        """
        new_vertex = self.get_vertex()
        self.weights[new_vertex] = 0

        # assert(len(vertices) == 2)

        connections = set()

        for v in vertices:

            # what are we gonna merge?
            for item in self.edges[v]:
                connections.add(item)

            # Add the definition of this vertex to the new vertex
            # self.merge_defs[new_vertex] = self.merge_defs.get(new_vertex, []) + [v]

            if v[0] == 's':
                self.defines[new_vertex] = self.defines.get(new_vertex, []) + [self.defines[v][0],
                                                                               self.defines[v][2]] + [
                    self.defines[v][1], self.defines[v][3]]
            else:
                self.defines[new_vertex] = self.defines.get(
                    new_vertex, []) + self.defines[v]

            self.weights[new_vertex] += 1

            # remove the old vertex, since it's been replaced by new_vertex
            remove_vertex(self, v)
            self.reduce_defines()
        # self.weights[new_vertex] = 2
        for connection in connections:
            self.edges[new_vertex].add(connection)
            self.edges[connection].add(new_vertex)

        return new_vertex

    def reduce_defines(self):
        """
        Make defines like this:

        define x0 2 124 124 3 4 125 127 5 5

        Into this:

        define x0 2 3 5 124 127

        That is, consolidate contiguous bulge region defines.
        """
        for key in self.defines.keys():
            if key[0] != 's':
                assert (len(self.defines[key]) % 2 == 0)
                new_j = 0

                while new_j < len(self.defines[key]):

                    j = new_j
                    new_j += j + 2

                    (f1, t1) = (int(self.defines[key][j]), int(
                        self.defines[key][j + 1]))

                    # remove bulges of length 0
                    if f1 == -1 and t1 == -2:
                        del self.defines[key][j]
                        del self.defines[key][j]

                        new_j = 0
                        continue

                    # merge contiguous bulge regions
                    for k in range(j + 2, len(self.defines[key]), 2):
                        if key[0] == 'y':
                            # we can have stems with defines like: [1,2,3,4]
                            # which would imply a non-existant loop at its end
                            continue

                        (f2, t2) = (int(self.defines[key][k]), int(
                            self.defines[key][k + 1]))

                        if t2 + 1 != f1 and t1 + 1 != f2:
                            continue

                        if t2 + 1 == f1:
                            self.defines[key][j] = str(f2)
                            self.defines[key][j + 1] = str(t1)
                        elif t1 + 1 == f2:
                            self.defines[key][j] = str(f1)
                            self.defines[key][j + 1] = str(t2)

                        del self.defines[key][k]
                        del self.defines[key][k]

                        new_j = 0

                        break

    def define_a(self, elem):
        """
        Returns the element define using the adjacent nucleotides (if present).

        If there is no adjacent nucleotide due to a chain break or chain end,
        then the nucleotide that is part of the element will be used instead.

        For stems, this always returns a list of length 4,
        for interior loops a list of length 2 or 4 and
        for other elements always a list of length 2.


        :param elem: An element name
        :returns: A list of integers
        """
        if self.defines[elem] == []:
            return self._define_a_zerolength(elem)
        return self._define_a_nonzero(elem)

    def _define_a_nonzero(self, elem):
        define = self.defines[elem]
        new_def = []
        for i in range(0, len(define), 2):
            new_def.append(max(define[i] - 1, 1))
            new_def.append(define[i + 1] + 1)
        return new_def

    def define_range_iterator(self, node, adjacent=False):
        """
        Return the ranges of the nucleotides in the define.

        In other words, if a define contains the following: [1,2,7,8]
        The ranges will be [1,2] and [7,8].

        :param adjacent: Use the nucleotides in the neighboring element which
                         connect to this element as the range starts and ends.
        :return: A list of two-element lists
        """
        if adjacent:
            define = self.define_a(node)
        else:
            define = self.defines[node]

        if define:
            yield [define[0], define[1]]
            if len(define) > 2:
                yield [define[2], define[3]]

class DotGraph(DotGraphConstructor):
    """
    dot graph, defined by:
    s: stem
    h: hairpin
    i: interior loop
    m: multiloop
    f: five-prime unpaired
    t: three-prime unpaired
    """
    def __init__(self,seq='',dot='',energy=0,prob=[],pairtuple=[],ratio=0,name=None):
        self.seq=seq
        self.prob=prob
        self.dot=dot
        self.energy=energy
        # self.pairtuple=pairtuples
        self.defines={}
        self.edges=defaultdict(set)
        self.weights={}
        self._name_counter=0
        self.pairtuple=pairtuple
        self.name=name
        self.ratio=ratio
        self.from_tuples(pairtuple)

    @property
    def seq_length(self):
        return len(self.seq)

    def get_elem(self, position):
        """
        Get the secondary structure element from a nucleotide position

        :param position: An integer or a fgr.RESID instance, describing the nucleotide number.
        """
        for k,i in self.defines.items():
            find=False
            for s,e in zip(i[0::2],i[1::2]):
                if s<=position<=e:
                    find=True
                    break
            if find:break
        return k

    def pairing_partner(self,i):
        """
        get parterner of pair
        """
        assert 0<i<self.seq_length+1, "nt index {} out of range {}".format(i,self.seq_length)
        return self.pairtuple[i-1][1]

    def define_residue_num_iterator(self,node,adjacent=True):
        """
        Iterate over the residue numbers that belong to this node.

        :param node: The name of the node
        """
        visited = set()

        for r in self.define_range_iterator(node, adjacent):
            for i in range(r[0], r[1] + 1):
                if i not in visited:
                    visited.add(i)
                    yield i

    def stem_iterator(self):
        """
        Iterator over all of the stems in the structure.
        """
        for d in self.defines.keys():
            if d[0] == 's':
                yield d

    def hloop_iterator(self):
        """
        Iterator over all of the hairpin in the structure.
        """
        for d in self.defines.keys():
            if d[0] == 'h':
                yield d

    def mloop_iterator(self):
        """
        Iterator over all of the multiloops in the structure.
        """
        for d in self.defines.keys():
            if d[0] == 'm':
                yield d

    def iloop_iterator(self):
        """
        Iterator over all of the interior loops in the structure.
        """
        for d in self.defines.keys():
            if d[0] == 'i':
                yield d

    def floop_iterator(self):
        """
        Yield the name of the 5' prime unpaired region if it is
        present in the structure.
        """
        for d in self.defines.keys():
            if d[0] == 'f':
                yield d

    def tloop_iterator(self):
        """
        Yield the name of the 3' prime unpaired region if it is
        present in the structure.
        """
        for d in self.defines.keys():
            if d[0] == 't':
                yield d

    def stem_length(self,key):
        """
        Get the length of a particular element. If it's a stem, it's equal to
        the number of paired bases. If it's an interior loop, it's equal to the
        number of unpaired bases on the strand with less unpaired bases. If
        it's a multiloop, then it's the number of unpaired bases.
        """
        d = self.defines[key]
        if key[0] in 'shmft':
            return (d[1] - d[0]) + 1
        else:
            return min((d[1] - d[0]) + 1,(d[3] - d[2]) + 1)

    def stem_bp_iterator(self, stem):
        """
        Iterate over all the base pairs in the stem.
        """
        assert stem[0] == "s"
        d = self.defines[stem]
        stem_length = self.stem_length(stem)
        for i in range(stem_length):
            yield (d[0] + i, d[3] - i)

    def plot_size(self):
        """
        estimate plot size
        """
        ViennaRNA.cvar.rna_plot_type=1
        coords = []
        vrna_coords = ViennaRNA.get_xy_coordinates(self.dot)
        for i in range(self.seq_length):
            coord = ( vrna_coords.get(i).X,
                     vrna_coords.get(i).Y)
            coords.append(coord)
        coords = np.array(coords)

        #rotate coordinates for best angle.
        rotate=[]
        for angle in range(-180,180,15):
            tempcoords=np.zeros_like(coords)
            for k,i in enumerate(coords):
                tempcoords[k,:]=np.array(rotate_coord((0,0),i,angle))
            tempwidth=np.max(tempcoords[:, 0])-np.min(tempcoords[:, 0])
            tempheight=np.max(tempcoords[:, 1])-np.min(tempcoords[:, 1])
            _=abs(tempheight-tempwidth)/max(tempheight,tempwidth)
            rotate.append((tempwidth,tempheight))
            if _<0.07:
                break

        return min(rotate,key=lambda x:abs(x[0]-x[1])/max(x[0],x[1]) )

    def plot_2d(self,ax=None,backbone_kwargs = {},basepair_kwargs={},
                text_kwargs={},ntnum_kwargs={},ele_kwargs={},**kwargs):
        """
        backbone_kwargs: pass to ax.plot for draw backbone.
        basepair_kwargs : color can be a matplotlib color map.
        text_kwargs : pass to ax.annotate for nt name
        ele_kwargs : pass to element name
        ntnum_kwargs:pass to nt number.
        """
        # get coordinates
        ViennaRNA.cvar.rna_plot_type=1
        coords = []
        vrna_coords = ViennaRNA.get_xy_coordinates(self.dot)
        for i in range(self.seq_length):
            coord = ( vrna_coords.get(i).X,
                     vrna_coords.get(i).Y)
            coords.append(coord)
        coords = np.array(coords)

        #rotate coordinates for best angle.
        rotate=[]
        for angle in range(-180,180,15):
            tempcoords=np.zeros_like(coords)
            for k,i in enumerate(coords):
                tempcoords[k,:]=np.array(rotate_coord((0,0),i,angle))
            tempwidth=np.max(tempcoords[:, 0])-np.min(tempcoords[:, 0])
            tempheight=np.max(tempcoords[:, 1])-np.min(tempcoords[:, 1])
            _=abs(tempheight-tempwidth)/max(tempheight,tempwidth)
            rotate.append((angle,_))
            if _<0.07:
                break
        bestangle=min(rotate,key=lambda x:x[1])[0]
        for k,i in enumerate(coords):
            coords[k,:]=np.array(rotate_coord((0,0),i,bestangle))


        # find all breaks:
        breaks = [0]+[i for i,j in enumerate(self.seq) if j == "+"]+[self.seq_length]

        # start plotting
        if not ax:
            fig,ax =plt.subplots(1,figsize=(8,6),)

        # draw backbone
        bkwargs={"color":"black", "zorder":0}
        bkwargs.update(backbone_kwargs)
        for index, (start, end) in enumerate(zip(breaks[:-1], breaks[1:])):
            # each time skip a "+" need to increase start by 1.
            start += index
            ax.plot(coords[start:end,0], coords[start:end,1], **bkwargs)

        # draw stem base pair and probability of pairing.
        basepairs = []
        basepairprob=[]
        for s in self.stem_iterator():
            for p1, p2 in self.stem_bp_iterator(s):
                basepairs.append([coords[p1-1], coords[p2-1]])
                basepairprob.append(max(self.prob[p1-1],self.prob[p2-1]))
        if basepairs:
            basepairs = np.array(basepairs)
            bpkwargs = { "zorder":0, "linewidth":3,"linestyle":"-"}
            bpkwargs.update(basepair_kwargs)
            colormapper=scalar_to_rgb(basepairprob+[kwargs.pop('maxprob',0)],bpkwargs.pop('color','cool'))
            for i,j,p in zip(basepairs[:,:,0],basepairs[:,:,1],basepairprob):
                ax.plot(i,j,color=colormapper(p),**bpkwargs)

        # draw circle and letters
        fp = FontProperties(family="monospace", weight='bold')

        vocal="ATGCUWSMKRYBDHVN"
        LETTERS = {i:TextPath( (-2, -2), i.upper(), size=6, prop=fp ) for i in vocal+vocal.lower()+'-+'}
        def default():
            return 'black'
        ntcolor=defaultdict(default)
        ntcolor.update(dict(zip('ATGCU',['red','green','sienna','blue','green'])))
        for i, coord in enumerate(coords):
            nucleotide=self.seq[i]
            # skip drawing breaks
            if nucleotide == '+':
                continue
            circle = plt.Circle((coord[0], coord[1]),
                                edgecolor='black', radius=2.85,facecolor=ntcolor[nucleotide])#"white"
            ax.add_artist(circle)
            txtkwargs={"fontweight":"bold","fontsize":6}
            txtkwargs.update(text_kwargs)
            if self.seq:
                letter=self.seq[i]
                text = LETTERS[letter]
                t = mpl.transforms.Affine2D().translate(coord[0],coord[1]) + ax.transData

                p = PathPatch(
                    text, lw=0,fc='white',transform=t)#fc=ntcolor[letter]
                ax.add_artist(p)


        # draw nt index from 5 to 10.
        all_coords=list(coords)
        nt_kwargs = {"color":"black","fontsize":10}
        nt_kwargs.update(ntnum_kwargs)
        # ntnum_kwargs.update(text_kwargs)
        for index, (start, end)in enumerate(zip(breaks[:-1], breaks[1:])):
            for label in range(5, end-start+1, 5):
                # We try different angles
                nt = start + label + index
                annot_pos = _find_annot_pos_on_circle(nt, all_coords, self)
                if annot_pos is not None:
                    ax.annotate(str(label), xy=coords[nt-1], xytext=annot_pos,
                                arrowprops={"width":0.5, "headwidth":0.5, "color":"gray"},
                                ha="center", va="center", zorder=0, **nt_kwargs)
                    all_coords.append(annot_pos)


        # for nt in range(5, self.seq_length, 5):
        #     # We try different angles
        #     annot_pos = _find_annot_pos_on_circle(nt, all_coords, self)
        #     if annot_pos is not None:
        #         label = nt
        #         # decide if shift by an index for nt position.
        #         near_break  = self.seq[0:nt].rfind('+')
        #         if near_break>=0:
        #             label -= near_break

        #         ax.annotate(str(label), xy=coords[nt-1], xytext=annot_pos,
        #                     arrowprops={"width":0.5, "headwidth":0.5, "color":"gray"},
        #                     ha="center", va="center", zorder=0, **nt_kwargs)
        #         all_coords.append(annot_pos)

        # annotate stemloop elements.
        elekwargs = {"color":"black","fontsize":10}
        elekwargs.update(ele_kwargs)
        annotations={}
        _annotate_rna_plot(ax, self, all_coords, annotations, elekwargs)
        datalim = ((min(list(coords[:, 0]) + [ax.get_xlim()[0]]),
                    min(list(coords[:, 1]) + [ax.get_ylim()[0]])),
                   (max(list(coords[:, 0]) + [ax.get_xlim()[1]]),
                    max(list(coords[:, 1]) + [ax.get_ylim()[1]])))

        # width = datalim[1][0] - datalim[0][0]
        # height = datalim[1][1] - datalim[0][1]
        # print(width,height)
        energy = "{:.1f},{:.1f},{:.1f}".format(*self.energy) if isinstance(self.energy,tuple) else round(self.energy,1)
        edratio="{},{},{}".format(*self.ratio) if isinstance(self.ratio,tuple) else self.ratio
        ax.set_title("{}, dG={}, ED={}".format(self.name,energy,edratio))
        ax.set_aspect('equal', 'datalim')
        ax.update_datalim(datalim)
        ax.autoscale_view()
        ax.set_axis_off()

class Structure_eq():
    """
    class to judge if two structures are equal using various methods
    this class can be used as a function.
    """
    def __init__(self,method,threshold=None):
        self.method=method
        self.threshold=threshold

    def __call__(self,*args):
        return getattr(self,self.method)(*args)

    def match(self,a,b):
        return a==b

    def starmatch(self,a,b):
        for i,j in zip(a,b):
            if i!=j and i !='*' and j !='*':
                return False
        return True

    def hamming(self,s1,s2):
        return sum([i!=j for i,j in zip(s1,s2)]) <= self.threshold

    def tree(self,s1,s2):
        xstruc = ViennaRNA.expand_Full(s1)
        T1 = ViennaRNA.make_tree(xstruc)
        xstruc = ViennaRNA.expand_Full(s2)
        T2 = ViennaRNA.make_tree(xstruc)
        ViennaRNA.edit_backtrack = 1
        tree_dist = ViennaRNA.tree_edit_distance(T1, T2)
        return tree_dist<=self.threshold

    def basepair(self,s1,s2):
        return ViennaRNA.bp_distance(s1,s2) <= self.threshold

class SPT_collector():
    """
    container class for dotbracket, probability and tuples
    this container will only fill in dots thats already initiated.
    """
    def __init__(self,order=(1,1,0,1)):
        self.data={}
        self.initiated=False
        self.dataaggregateorder=order
    def init(self,s,*args):
        assert len(args)==len(self.dataaggregateorder),('data length must equal dataaggregateorder')
        self.initiated=True
        for d,*data in zip(s,*args):
            if d not in self.data:
                self.data[d]=list(data)+[1]
            else:
                self.add(d,*data)

    def fill(self,seq,s,*args):
        if self.data or self.initiated:
            self.intersect(seq,s,*args)
        else:
            self.init(s,*args)

    def seq_str_eq(self,seq,s1,s2):
        for n,s,t in zip(seq,s1,s2):
            if n=='-':
                continue
            else:
                if s!=t:
                    return False
        return True

    def intersect(self,seq,s,*args):
        self.data={i:j for i,j in self.data.items() if i in s}
        new = {}
        for d,*data in zip(s,*args):
            for k in self.data:
                if self.seq_str_eq(seq,d,k):
                    *olddata,count=self.data[k]
                    new[k]=self.dataaggregate_method(olddata,data,count)
        self.data=new

    def dataaggregate_method(self,old,new,count):
        result=[]
        for a,o,n in zip(self.dataaggregateorder,old,new):
            if a:
                result.append((o*count+n)/(count+1))
            else:
                result.append(o)
        return result

    def add(self,d,*data):
        *olddata,count=self.data[d]
        self.data[d]=self.dataaggregate_method(olddata,data,count)

    def output(self):
        s=[k for k,i in self.data.items()]
        r=[]
        for z in range(len(self.dataaggregateorder)):
            r.append([i[z] for k,i in self.data.items()])
        return (s,*r)

class Design_collector():
    """
    collector class for designed structures and their associated FontProperties,
    such as energy and etc.
    a limit is set at beginning to limit max capacity of the class.
    a function can be passed to determine which entries will be retained after overfilled
    the class..
    """
    def __init__(self,limit=100,func=None):
        self.limit=limit
        self.func=func
        self.data=[]
        self.edge=None

    def add(self,entry):
        if entry is None:
            return 0
        func=self.func
        # if (self.edge is None) or (func(entry) >= self.edge):
        self.edge = func(entry)
        heapq.heappush(self.data,(self.edge,entry))
        if len(self.data)>self.limit:
            heapq.heappop(self.data)

    def collect(self):
        a=[heapq.heappop(self.data) for i in range(len(self.data))]
        a.reverse()
        return [i[1] for i in a]


def any_difference_of_one(stem, bulge):
    """
    See if there's any difference of one between the two
    ends of the stem [(a,b),(c,d)] and a bulge (e,f)

    :param stem: A couple of couples (2 x 2-tuple) indicating the start and end
                 nucleotides of the stem in the form ((s1, e1), (s2, e2))
    :param bulge: A couple (2-tuple) indicating the first and last position
                  of the bulge.
    :return: True if there is an overlap between the stem nucleotides and the
                  bulge nucleotides. False otherwise
    """
    for stem_part in stem:
        for part in stem_part:
            for bulge_part in bulge:
                if abs(bulge_part - part) == 1:
                    return True
    return False

def remove_vertex(bg, v):
    """
    Delete a node after merging it with another

    :param v: The name of the node
    """
    # delete all edges to this node
    for key in bg.edges[v]:
        bg.edges[key].remove(v)

    for edge in bg.edges:
        if v in bg.edges[edge]:
            bg.edges[edge].remove(v)

    # delete all edges from this node
    del bg.edges[v]
    del bg.defines[v]

def relabel_node(bg, old_name, new_name):
    """
    Change the name of a node.

    param old_name: The previous name of the node
    param new_name: The new name of the node
    """
    #log.debug("Relabelling node {} to {}".format(old_name, new_name))
    # replace the define name
    define = bg.defines[old_name]

    del bg.defines[old_name]
    bg.defines[new_name] = define

    # replace the index into the edges array
    edge = bg.edges[old_name]
    del bg.edges[old_name]
    bg.edges[new_name] = edge

    # replace the name of any edge that pointed to old_name
    for k in bg.edges.keys():
        new_edges = set()
        for e in bg.edges[k]:
            if e == old_name:
                new_edges.add(new_name)
            else:
                new_edges.add(e)
        bg.edges[k] = new_edges

def rotate_coord(origin, point, angle):
    """
    Rotate a point counterclockwise by a given angle around a given origin.
    The angle should be given in radians.
    """
    angle=angle/180*np.pi
    ox, oy = origin
    px, py = point
    qx = ox + np.cos(angle) * (px - ox) - np.sin(angle) * (py - oy)
    qy = oy + np.sin(angle) * (px - ox) + np.cos(angle) * (py - oy)
    return qx, qy

def scalar_to_rgb(scalar,map):
    """
    map a group of scalar value to a color map.
    return a mapper function.
    """
    cm=plt.get_cmap(map)
    cNorm  = colors.Normalize(vmin=np.min(scalar), vmax=np.max(scalar))
    scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
    return scalarMap.to_rgba

def magnitude(vec):
    '''
    Return the magnitude of a vector `(|V|)`.

    This is guaranteed for arbitrary dimensions of vec.

    :param vec: The vector in question.
    :return: The magnitude of the vector.
    '''
    # return np.linalg.norm(vec) #A lot of overhead, if used for a single vector
    return np.sqrt(np.dot(vec, vec))

def vec_distance(vec1, vec2):
    """
    The (euclidean) distance between two points vec1 and vec2.

    This is guaranteed to work for arbitrary but equal dimensions of vec1 and vec2.

    :param vec1, vec2: A list or np.array of floats
    :returns: A float
    """
    vec1 = np.asarray(vec1)
    vec2 = np.asarray(vec2)
    direction = vec2 - vec1
    return np.sqrt(np.dot(direction, direction))

def _clashfree_annot_pos(pos, coords):
    for c in coords:
        dist = vec_distance(c, pos)
        #log.debug("vec_dist=%s", dist)
        if dist<14:
            return False
    return True

def _find_annot_pos_on_circle(nt, coords, cg):
    for i in range(5):
        for sign in [-1,1]:
            a = np.pi/4*i*sign
            if cg.get_elem(nt)[0]=="s":
                bp = cg.pairing_partner(nt)
                anchor = coords[bp-1]
            else:
                anchor =np.mean([ coords[nt-2], coords[nt]], axis=0)
            vec = coords[nt-1]-anchor
            vec=vec/magnitude(vec)
            rotated_vec =  np.array([vec[0]*np.cos(a)-vec[1]*np.sin(a),
                                     vec[0]*np.sin(a)+vec[1]*np.cos(a)])
            annot_pos = coords[nt-1]+rotated_vec*18
            if _clashfree_annot_pos(annot_pos, coords):

                return annot_pos
    # print("Annot pos on %s not found." % (str(nt)))
    return None

def _annotate_rna_plot(ax, cg, coords, annotations, text_kwargs):
    # Plot annotations
    annot_dict = { elem:elem for elem in cg.defines}
    if annotations is None:
        annot_dict={elem:"" for elem in cg.defines}
    else:
        annot_dict.update(annotations)
    stem_coords = {}
    for stem in cg.stem_iterator():
        stem_start =  np.mean([coords[cg.defines[stem][0]-1],
                               coords[cg.defines[stem][3]-1]],
                               axis=0)
        stem_end =  np.mean([coords[cg.defines[stem][1]-1],
                               coords[cg.defines[stem][2]-1]],
                               axis=0)
        stem_center = np.mean([stem_start, stem_end], axis=0)
        stem_coords[stem]=(stem_start, stem_center, stem_end)
        if annot_dict[stem]:
            stem_vec = stem_end - stem_start
            norm_vec = (stem_vec[1], -stem_vec[0])
            norm_vec/=magnitude(norm_vec)
            annot_pos = np.array(stem_center)+23*norm_vec
            #log.debug("Checking clashfree for %s, %s", stem, annot_pos)
            if not _clashfree_annot_pos(annot_pos, coords):
                # print("Cannot annotate %s as %s ON THE RIGHT HAND SIDE, because of insufficient space. Trying left side..." % (stem, annot_dict[stem]))
                annot_pos = np.array(stem_center)-23*norm_vec
                # print("Checking clashfree OTHER SIDE for %s, %s" % (stem, annot_pos))
                if not _clashfree_annot_pos(annot_pos, coords):
                    # print("Cannot annotate %s as '%s', because of insufficient space." % (stem, annot_dict[stem]))
                    annot_pos = None
            #log.debug("%s", annot_pos)
            if annot_pos is not None:
                ax.annotate(annot_dict[stem], xy=annot_pos,
                            ha="center", va="center", **text_kwargs )
    for hloop in cg.hloop_iterator():
        hc = []
        for nt in cg.define_residue_num_iterator(hloop, adjacent=True):
            hc.append(coords[nt-1])
        annot_pos = np.mean(hc, axis=0)
        if _clashfree_annot_pos(annot_pos, coords):
            ax.annotate(annot_dict[hloop], xy=annot_pos,
                        ha="center", va="center", **text_kwargs )
        else:
            # print("Cannot annotate %s as '%s' ON THE INSIDE, because of insufficient space. Trying outside..." % (hloop, annot_dict[hloop]))
            nt1, nt2 = cg.define_a(hloop)
            start = np.mean([coords[nt1-1], coords[nt2-1]], axis=0)
            vec = annot_pos-start
            annot_pos = annot_pos+vec*3
            if _clashfree_annot_pos(annot_pos, coords):
                ax.annotate(annot_dict[hloop], xy=annot_pos,
                            ha="center", va="center", **text_kwargs )
            # else:
                # print("Cannot annotate %s as '%s', because of insufficient space." % ( hloop, annot_dict[hloop]))
    for iloop in cg.iloop_iterator():
        s1, s2 = cg.connections(iloop)
        annot_pos = np.mean([ stem_coords[s1][2], stem_coords[s2][0]], axis=0)
        if _clashfree_annot_pos(annot_pos, coords):
            ax.annotate(annot_dict[iloop], xy=annot_pos,
                        ha="center", va="center", **text_kwargs )
        else:
            # print("Cannot annotate %s as '%s' ON THE INSIDE, because of insufficient space. Trying outside..." % (iloop, annot_dict[iloop]))
            loop_vec = stem_coords[s2][0] - stem_coords[s1][2]
            norm_vec = (loop_vec[1], -loop_vec[0])
            norm_vec/=magnitude(norm_vec)
            annot_pos_p = np.array(annot_pos)+25*norm_vec
            annot_pos_m = np.array(annot_pos)-25*norm_vec
            # iloops can be asymmetric (more nts on one strand.)
            # plot the label on the strand with more nts.
            plus=0
            minus=0
            for nt in cg.define_residue_num_iterator(iloop):
                if vec_distance(annot_pos_p, coords[nt-1])<vec_distance(annot_pos_m, coords[nt-1]):
                    plus+=1
                else:
                    minus+=1
            if plus>minus:
                if _clashfree_annot_pos(annot_pos_p, coords):
                    ax.annotate(annot_dict[iloop], xy=annot_pos_p,
                                ha="center", va="center", **text_kwargs )
                # else:
                    # print("Cannot annotate %s as '%s' (only trying inside and right side), because of insufficient space." % (iloop, annot_dict[iloop]))

            else:
                if _clashfree_annot_pos(annot_pos_m, coords):
                    ax.annotate(annot_dict[iloop], xy=annot_pos_m,
                                ha="center", va="center", **text_kwargs )
                # else:
                    # print("Cannot annotate %s as '%s' (only trying inside and left side), because of insufficient space." % (iloop, annot_dict[iloop]))
    for mloop in chain(cg.floop_iterator(), cg.tloop_iterator(), cg.mloop_iterator()):
        nt1, nt2 = cg.define_a(mloop)
        res = list(cg.define_residue_num_iterator(mloop))
        if len(res)==0:
            anchor = np.mean([coords[nt1-1], coords[nt2-1]], axis=0)
        elif len(res)%2==1:
            anchor = coords[res[int(len(res)//2)]-1]
        else:
            anchor =  np.mean([ coords[res[int(len(res)//2)-1]-1],
                                coords[res[int(len(res)//2)]-1] ],
                              axis=0)
        loop_vec = coords[nt1-1] - coords[nt2-1]
        norm_vec = (loop_vec[1], -loop_vec[0])
        norm_vec/=magnitude(norm_vec)
        annot_pos = anchor - norm_vec*18
        if _clashfree_annot_pos(annot_pos, coords):
            ax.annotate(annot_dict[mloop], xy=annot_pos,
                        ha="center", va="center", **text_kwargs )

def panel_count(n,maxcol):
    r=int(np.ceil(np.sqrt(n)))
    if r <=maxcol:
        col=int(np.ceil(n/r))
        return (r,col)
    else:
        row=int(np.ceil(n/maxcol))
        return (row,maxcol)

def dotbracket_to_tuple(struct):
    """
    Converts arbitrary structure in dot bracket format to pair table (ViennaRNA format).
    """
    struct=struct.replace("+",'.')

    bracket_left = "([{<ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    bracket_right = ")]}>abcdefghijklmnopqrstuvwxyz"

    if len(struct) == 0:
        raise ValueError("Cannot convert empty structure to pairtable")
    pt = [0] * ((len(struct) + 1) - struct.count("+"))
    pt[0] = len(struct) - struct.count("+")

    stack = defaultdict(list)
    inverse_bracket_left = dict(zip(bracket_left,range(len(bracket_left))))
    inverse_bracket_right =  dict(zip(bracket_right,range(len(bracket_left))))

    i = 0
    for a in struct:
        if a == '+':
            continue
        i += 1
        # print i,a, pt
        if a == ".":
            pt[i] = 0
        else:
            if a in inverse_bracket_left:
                stack[inverse_bracket_left[a]].append(i)
            else:
                assert a in inverse_bracket_right , ('NOt in right {}'.format(a))
                if len(stack[inverse_bracket_right[a]]) == 0:
                    raise ValueError('Too many closing brackets!')
                j = stack[inverse_bracket_right[a]].pop()
                pt[i] = j
                pt[j] = i

    if any([len(stack[i]) != 0  for i in range(len(bracket_left))]):
        raise ValueError('Too many opening brackets!')

    tuples = []
    for i, p in enumerate(pt[1:]):
        tuples += [(i + 1, p)]

    return tuples

def ensemble_to_prob(ensemble):
    """
    convert a ensemble of dotbrackets to probability of each pair
    """
    ens=np.array([ [k!='.' for k in i] for i in ensemble],int)
    ens=ens.mean(axis=0)
    return ens

def kdistance(s1,s2):
    """
    calculate hamming distance.
    """
    return sum([i!=j for i,j in zip(s1,s2)])

def cluster_and_center(list_of_seq, distance,cluster='hamming',center='energy'):
    """
    use different methods to cluster structures and pick the center of each cluster.
    """
    if not distance:
        list_of_seq.sort(key=lambda x:x[1])
        return [i[0] for i in list_of_seq]
    methods={'hamming':kdistance,'tree':tree_edit_distance,'basepair':basepair_distance}
    function = methods[cluster]
    result_key = [list_of_seq[0][0]]
    result = {list_of_seq[0][0]: []}
    for k,(i,e) in (enumerate(list_of_seq)):
        temp = i
        discalc=partial(function,s2=i)
        distlist = list(map(discalc,result_key))
        if min(distlist)<=distance:
            temp = result_key[distlist.index(min(distlist))]
        if temp == i:
            result_key.append(i)
            result.update({i: [(i,e)]})
        else:
            result[temp].append((i,e))

    result=[findcenter(j,method=center,clustermethod=cluster) for i,j in result.items()]
    result.sort(key=lambda x:np.mean(x[1]))
    return [i[0] for i in result]

def findcenter(listofseq,method,clustermethod):
    """
    find the center of a cluster using different methods.
    """
    methods={'hamming':kdistance,'tree':tree_edit_distance,'basepair':basepair_distance}
    func = methods.get(clustermethod,'hamming')
    if method=='distance':
        distance = dict.fromkeys(listofseq,0)
        for i,j in combinations(listofseq,2):
            dis=func(i[0],j[0])
            distance[i]+=dis
            distance[j]+=dis
        return min(distance.items(),key=lambda x:x[1])[0]
    elif method == 'energy':
        return min(listofseq,key = lambda x:x[1])

def filterlonelypair(seq_energy_pair):
    """
    remove structures that have lone pairs.
    """
    res=[]
    for i,j in seq_energy_pair:
        if '.).' in i or '.(.' in i:
            pass
        else:
            res.append((i,j))
    return res

def tree_edit_distance(s1,s2,):
    """
    calculate tree_edit_distance
    """
    xstruc = ViennaRNA.expand_Full(s1)
    T1 = ViennaRNA.make_tree(xstruc)
    xstruc = ViennaRNA.expand_Full(s2)
    T2 = ViennaRNA.make_tree(xstruc)
    ViennaRNA.edit_backtrack = 1
    tree_dist = ViennaRNA.tree_edit_distance(T1, T2)
    return tree_dist

def basepair_distance(s1,s2):
    """
    calculate basepair distance.
    """
    return ViennaRNA.bp_distance(s1,s2)

def resolve_pseudoknot(b):
    """
    sometimes Nupack pseudoknot structure is not noted correctly.
    this resolves it.
    e.g.
    ((({{{...}}})))
    will convert to be
    ((((((...))))))
    """
    b=list(b)
    indi=[0,0]
    temp=0
    startcount=False
    for i,j in enumerate(b):
        indi[1]=i
        if j=='{' and b[i+1]!='{':
            indi[0]=i
            startcount=True
            temp=0
            continue
        else:
            if startcount:
                if j=='{':
                    indi[0]=i
                    temp=0
                    startcount=False
                elif j=='.':
                    continue
                elif j=='(':
                    temp+=1
                elif j==')':
                    temp-=1
                else:
                    if temp ==0:
                        break
                    else:
                        indi[0]=i
                        temp=0
                        startcount=False
            else:
                indi[0]=i
    if indi[0]==indi[1]:
        return ''.join(b)
    else:
        b[indi[0]]='('
        b[indi[1]]=')'
        return resolve_pseudoknot(b)
