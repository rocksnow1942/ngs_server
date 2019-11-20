import pickle,copy
import matplotlib.pyplot as plt
import numpy as np
from itertools import product
import matplotlib as mpl
from matplotlib.text import TextPath
from matplotlib.patches import PathPatch
from matplotlib.font_manager import FontProperties
import pandas as pd
import seaborn as sns
from collections import Counter
import scipy.stats as ss
# from .._structurepredict import Structure

# alignment module
"""
alignmnet module
20170718:
modified for foldojo usage
"""
def IUPAC_codec(it):
    """
    give a list or string of letters return code.
    """
    seq=set(it)
    assert seq<=set('ATGCUWSMKRYBDHVN-+'),('{} not in IUPAC codes.'.format(seq-set('ATGCUWSMKRYBDHVN-')))
    if len(seq)==1:
        return list(it)[0]
    elif seq==set('AT'):return 'W'
    elif seq==set('CG'):return 'S'
    elif seq==set('AC'): return "M"
    elif seq==set('GT'): return "K"
    elif seq==set('AG'): return "R"
    elif seq==set('CT'): return "Y"
    elif seq==set('CGT'): return "B"
    elif seq==set('AGT'): return "D"
    elif seq==set('ACT'): return "H"
    elif seq==set('ACG'): return "V"
    elif seq==set('ATCG'): return "N"
    elif seq==set('+'):return "+"
    else:
        return IUPAC_codec(seq-set('-')).lower()

def IUPAC_decode(i):
    assert str(i) in 'ATGCUWSMKRYBDHVN+',('{} is not a IUPAC abbrv.'.format(i))
    code={'W':'AT','S':'CG','K':'GT','M':'AC','Y':'CT','R':'AG','V':'ACG','H':'ACT','D':'AGT','B':'CGT','N':'ATCG'}
    return code.get(i,i)


####################################
def lev_distance(s1,s2,threshold=1000):
    """
    calculate diagonally.stop at threshold. fastest.
    """
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    l1=len(s1)
    vertical=[0]
    horizontal=[0]
    for i in range(l1):
        char1=s1[i]
        char2=s2[i]
        newvertical=[i+1]
        newhorizontal=[i+1]
        for k in range(i):
            if char1==s2[k]:
                newvertical.append(vertical[k])
            else:
                newvertical.append(1+min(newvertical[-1],vertical[k],vertical[k+1]))
            if char2==s1[k]:
                newhorizontal.append(horizontal[k])
            else:
                newhorizontal.append(1+min(newhorizontal[-1],horizontal[k],horizontal[k+1]))
        last = vertical[-1] if char1==char2 else (1+min(newvertical[-1],newhorizontal[-1],vertical[-1]))
        newhorizontal.append(last)
        newvertical.append(last)
        currentmin = min(min(newhorizontal),min(newvertical))
        if currentmin>threshold:
            return currentmin
        vertical,horizontal=newvertical,newhorizontal
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
        currentmin=min(newhorizontal)
        if currentmin>threshold:
            return currentmin
        horizontal=newhorizontal
    return horizontal[-1]

##############################################################################
# Alignment modules
class Alignment():
    def __init__(self, sequence=[''], count=[], name=None,like=False):
        """
        to init a alignment, sequence and count must be lists,alignment shouln't have any nested structure.
        name will be the id of NGS sequence.
        """
        """
           A	G	C	T   -
           [9, -1, -3, -4, -3],
           [-1, 10, -5, -3, -3],
           [-3, -5, 8, 0, -3],
           [-4, -3, 0, 7, -3],
           [-3, -3, -3, -3, 5]])

           [5, -1, -3, -4, -3],
          [-1, 6, -5, -3, -3],
          [-3, -5, 4, -1, -3],
          [-4, -3, -1, 3, -3],
          [-3, -3, -3, -3, 1]
        """
        self.similarity_matrix = np.array([[2, -1, -1, -1, -1.1],
                                           [-1, 2, -1, -1, -1.1],
                                           [-1, -1, 2, -0.6, -1.1],
                                           [-1, -1, -0.6, 2, -1.1],
                                           [-1.1,  -1.1, -1.1, -1.1, 1]])
        if like:
            like.__dict__.pop('ks',None)
            self.__dict__ = copy.deepcopy(like.__dict__)
            self.seq = ['']*len(like.seq)
            self.freq = []
        else:
            self.seq = sequence if isinstance(sequence, list) else [sequence]
            count = count if isinstance(count, list) else [count]
            self.count = count if count else [1]*len(self.seq)
            self.freq = self.freq_calc(self.seq, self.count)
            self.offset = [0]*len(self.seq)
            self.name = name
            self.up = None
            self.down = None
            self.up_down = len(self.seq)
            self._align_score = 100

    def __repr__(self):
        return "Alignment {}:{}".format(self.name,len(self.seq))

    def __str__(self):
        return '\n'.join([i + '\t' + str(j) for i, j in zip(self.seq, self.count)])

    def __eq__(self,b):
        return (set(self.seq) == set(b.seq)) and (self.name==b.name)

    def _collapse(self, collapse):
        def hamming(a, b):
            return sum([i != j for i, j in zip(a, b)])
        end = self.up_down
        seq, count, offset = [self.seq[0]], [self.count[0]], [self.offset[0]]
        counter = self.count[0]
        for s, c, o in zip(self.seq[1:end], self.count[1:end], self.offset[1:end]):
            if hamming(seq[-1], s) > collapse:
                seq.append(s)
                count.append(c)
                offset.append(o)
                counter = c
            else:
                count[-1] += c
                if c > counter:
                    seq[-1]=s
                    offset[-1]=o
                    counter=c
        seq_, count_, offset_ = [], [], []
        if len(self.seq) > self.up_down:
            seq_, count_, offset_ = [self.seq[end]], [
                self.count[end]], [self.offset[end]]
            counter = self.count[end]
            for s, c, o in zip(self.seq[end+1:], self.count[end+1:], self.offset[end+1:]):
                if hamming(seq_[-1], s) > collapse:
                    seq_.append(s)
                    count_.append(c)
                    offset_.append(o)
                    counter = c
                else:
                    count_[-1] += c
                    if c > counter:
                        seq_[-1]=s
                        offset_[-1]=o
                        counter=c
        return (seq, count, offset), (seq_, count_, offset_)

    def format(self, id=False, reverseindex=False,maxlength=0,count=False, offset=False, collapse=0,order=False,index=False,link=False):
        """
        option to show ID or Count number or Offset
        collapse will collapse sequence with a hamming distance < given number.
        order will rearrange sequence according to count number.
        """
        if collapse != 0:
            up, down = self._collapse(collapse)
        else:
            up = (self.seq[:self.up_down],
                  self.count[:self.up_down], self.offset[:self.up_down])
            down = (self.seq[self.up_down:],
                    self.count[self.up_down:], self.offset[self.up_down:])
        _string1 = [i + ('\t'+str(self.up))*id+('\t'+str(j))*count+('\t'+str(k))*offset
                             for i, j, k in zip(*up)]
        _string2 = [i + ('\t'+str(self.down))*id+('\t' + str(j))*count+('\t'+str(k))*offset
                             for i, j, k in zip(*down)]
        _string1.extend(_string2)
        counts = up[1]
        counts.extend(down[1])
        if order:
            _string1 = [i for _,i in sorted(zip(counts,_string1),reverse=True)]
        if link and len(self.seq)>1:
            linkers=[]
            for i in range(len(_string1)-1):
                linker=''
                for i,j in zip(_string1[i],_string1[i+1]):
                    if i==j:
                        linker+='|'
                    else:
                        linker+='*'
                linkers.append(linker)
            _string1 = [i for p in zip(_string1,linkers) for i in p]+_string1[-1:]

        if reverseindex:
            _string1=[i[::-1] for i in _string1]

        # indexing
        if index:
            length = len(self)
            digits = int(np.log10(length))+1
            index = ['']*digits
            for i in range(1,length+1):
                for j in range(digits):
                    if i % (5) ==0:
                        index[j]+=str(i//(10**(digits-1-j)))[-1]
                    else:
                        index[j]+='-'
            _string1=index+_string1

        if reverseindex:
            _string1=[i[::-1] for i in _string1]

        if maxlength:
            chunks = int(len(_string1[0])/maxlength) + 1*bool(len(_string1[0])%maxlength)
            newstring=[]
            for i in range(chunks):
                for j in _string1:
                    newstring.append(j[i*maxlength:(i+1)*maxlength])
                newstring.append('='*maxlength)
            _string1=newstring[0:-1]

        return ('\n').join(_string1)

    def __len__(self):
        return len(self.freq)

    def __iter__(self):
        return iter(self.rep_seq())

    def __getitem__(self, i):
        return [k[i] for k in self.seq], self.freq[i]

    def copy(self):
        return copy.deepcopy(self)

    def rep_seq(self, count=True):
        m = 'AGCT-'
        s = ''
        for i in self._freq(count):
            index = np.argmax(i)
            s += m[index]
        return s

    def iupac(self):
        result=''
        for i in zip(*self.seq):
            result+=IUPAC_codec(i)
        return result


    def _freq(self, count=True):
        a = self.freq if count else self.freq_calc(self.seq)
        return a

    def append(self, s):
        if isinstance(s, str):
            self.freq.extend([np.array([i=='A', i=='G', i=='C', i=='T', i in '-I'],int) for i in s])
            self.seq = [i+s for i in self.seq]
        else:
            self.freq.extend(s[1] if isinstance(s[1],list) else [s[1]])
            self.seq = [i+j for i, j in zip(self.seq, s[0])]
        return self

    def _replaceI(self):
        if 'I' in self.seq[0]:
            self.seq = [i.replace('I', '-') for i in self.seq]
        return self

    def extend(self, align, name,score):
        self_count = sum(self.count)
        align_count = sum(align.count)
        s = self_count/(self_count+align_count)
        al = align_count/(self_count+align_count)
        self.up_down = len(self.seq)
        self.seq.extend(align.seq)
        self.count.extend(align.count)
        self.offset.extend(align.offset)
        self.up = self.name
        self.name = name
        self.down = align.name
        self.freq = [i*s+j*al for i, j in zip(self.freq, align.freq)]
        self._align_score=score
        return self

    def reverse(self):
        self.freq = self.freq[::-1]
        self.seq = [i[::-1] for i in self.seq]
        return self

    def endswith(self, s):
        return self.seq[0].endswith(s)

    def refresh_freq(self):
        self.freq = self.freq_calc(self.seq, self.count)

    def remove_null(self):
        """remove sequence with 0 counts,
        update self.seq,self.up_down and self.count, self.offset,"""
        # remove up:
        new = []
        for i,j,k in zip(self.count[0:self.up_down],self.offset[0:self.up_down],self.seq[0:self.up_down]):
            if i >0:
                new.append((i,j,k))
        newupdown=len(new)
        for i,j,k in zip(self.count[self.up_down:],self.offset[self.up_down:],self.seq[self.up_down:]):
            if i >0:
                new.append((i,j,k))
        self.count=[i[0] for i in new]
        self.offset=[i[1] for i in new]
        self.seq=[i[2] for i in new]
        self.up_down=newupdown
        return self

    def freq_calc(self, list_of_seq, count=False):
        """
        return frequency list with order of AGCT-
        """
        list_of_seq = [list_of_seq] if isinstance(
            list_of_seq, str) else list_of_seq
        seq_c = len(list_of_seq)
        if seq_c == 0:
            result = []
        else:
            count = (np.array(count) /
                             sum(count) if count else np.full(seq_c, 1.0/seq_c))
            count = count.reshape(-1, 1)
            A_ = np.sum(np.multiply(np.array(
                [[k == 'A' for k in list(i)] for i in list_of_seq], float), count), axis=0)
            G_ = np.sum(np.multiply(np.array(
                [[k == 'G' for k in list(i)] for i in list_of_seq], float), count), axis=0)
            C_ = np.sum(np.multiply(np.array(
                [[k == 'C' for k in list(i)] for i in list_of_seq], float), count), axis=0)
            T_ = np.sum(np.multiply(np.array(
                [[k == 'T' for k in list(i)] for i in list_of_seq], float), count), axis=0)
            gap = np.sum(np.multiply(np.array(
                [[k == '-' for k in list(i)] for i in list_of_seq], float), count), axis=0)
            result = [np.array(i) for i in zip(A_, G_, C_, T_, gap)]
        return result

    def save(self, save=False):
        save = save if save else str(self.name)+'_align'
        with open(save, 'wb') as f:
            pickle.dump(self, f)

    def entropy(self, count=True):
        freq = np.array(self._freq(count))
        a = freq*((np.ma.log(freq)/np.log(2)).filled(0))
        entropy = -np.sum(a, axis=1)
        return entropy

    def align_score(self, mode=1, count=True):
        """
        score of the alignment.
        mode 0 calculated based on shannon information
        mode 1 calculated based on the similarity of sequences in the last alignment event.
        mode 2 calucated on sequence convergeness.
        """
        if mode == 0:
            return 100-np.mean(self.entropy(count))*100/2.321928094887363
        elif mode == 1:
            if not self.__dict__.get('_align_score',False):
                self._align_score = 100
            return self._align_score
        elif mode == 2:
            _freq = self._freq(count)
            correct = np.zeros_like(self.similarity_matrix)
            correct[-1, -1] = self.similarity_matrix[-1, -1]
            freq = np.array(_freq)
            score = np.matmul(np.reshape(
                freq, (-1, 5, 1)), np.reshape(freq, (-1, 1, 5)))*(self.similarity_matrix-correct)
            result = np.sum(score)
            max_freq = np.zeros_like(freq)
            max_freq[np.arange(len(max_freq)), freq.argmax(1)] = 1
            max_score = np.matmul(np.reshape(
                max_freq, (-1, 5, 1)), np.reshape(max_freq, (-1, 1, 5)))*self.similarity_matrix
            return 100.0*result/np.sum(max_score)

    def matrix(self, a, b, gap_penalty, gapext, count=True,dis=False):
        """
        b are alignments
        calculate the directional matrix. each element is a integer of X,LLL,UUU;
        X = 1 if going diagonally. LLL = steps going left, UUU = steps going upwards.
        """
        m = np.zeros((len(a)+1, len(b)+1), float)
        direction_matrix = np.zeros((len(a)+1, len(b)+1), int)
        direction_matrix[0, 1:] = [1000*(i+1) for i in range(len(b))]
        direction_matrix[1:, 0] = [(i+1) for i in range(len(a))]
        a = a._freq(count)
        b = b._freq(count)
        for i, j in product(range(direction_matrix.shape[0]), range(direction_matrix.shape[1])):
            if i == 0 or j == 0:
                m[i, j] = -i*gapext-j*gapext-(gap_penalty-gapext)*(int(i!=j))
            else:
                score = np.sum(np.matmul(np.reshape(
                    a[i - 1], (-1, 1)), np.reshape(b[j - 1], (1, -1))) * self.similarity_matrix)
                match = m[i - 1, j - 1] + score
                # leftcorr = 1-b[j - 1][-1]
                # upcorr = 1-a[i - 1][-1]
                l_index,left = max(enumerate(m[i, j - k-1] - gap_penalty
                           - k*gapext for k in range(j)),key=lambda x:x[1])
                u_index,up = max(enumerate(m[i - k-1, j] - gap_penalty
                         - k*gapext for k in range(i)),key=lambda x:x[1])
                max_ = max(match, up, left)
                m[i, j] = max_
                direction_matrix[i, j] = (
                    max_ == left)*(l_index+1) * 1000 + (max_ == match)*1000000 + (max_ == up)*(u_index+1)*1
        # np.savetxt('_matrix_m.txt',m,fmt='%4d',delimiter=' ')
        # np.savetxt('_matrix_d.txt',direction_matrix,fmt='%4d',delimiter=' ')
        # print(m)
        # print(direction_matrix)
        return direction_matrix if not dis else (direction_matrix,m[-1,-1])

    def traceback(self, m, seq_a, seq_b, record=None):
        if record == None:
            record = [Node(m.shape[0]-1, m.shape[1]-1,
                           a=Alignment(like=seq_a), b=Alignment(like=seq_b))]
        new_record = []
        for node in record:
            index = node.index
            if index == (0, 0):
                result = [i for i in record if i.index == (0, 0)]
                result = sorted(result, key=lambda x: x.qc())
                return result[0].a.reverse()._replaceI(), result[0].b.reverse()._replaceI()
            direction = m[index]
            new_record.extend(node.add_children(
                index, direction, seq_a, seq_b))
        if len(new_record) > 50:
            new_record = sorted(new_record, key=lambda x: x.qc())[:15]
        return self.traceback(m, seq_a, seq_b, record=new_record)

    def align(self, seq, gap=4, gapext=1, offset=True, name=None, count=True,**kwargs):
        """
        align self to a given alignment.
        offset = False will not adjust offset.
        offset = 'kmmer' or 'sw' will use kmmer method or sw method to adjust offset of smaller count alignment.
        """
        if not isinstance(seq, Alignment):
            seq = Alignment(seq)
        if offset:
            seq_a, seq = self.adjust_offset(seq, offset=offset, count=count,**kwargs)
        else:
            seq_a = self
        m = self.matrix(seq_a, seq, gap_penalty=gap,
                        gapext=gapext, count=count)
        r, e = self.traceback(m, seq_a, seq)
        distance = r._nw_distance(e,count=count)
        if kwargs.get('nw_distance',False):
            return distance
        else:
            score = (1-distance)*100.0
            return r.extend(e, name,score)

    def _index_backcal(self, a, b, index):
        a_ = 0
        while a.startswith('-'):
            a_ += 1
            a = a[1:]
        b_ = 0
        for k, i in enumerate(b):
            if i != '-':
                b_ += 1
            if b_ == index:
                break
        b = b[k+1:]
        b_ = 0
        while b.startswith('-'):
            b_ += 1
            b = b[1:]
        return k+1+max(0, b_-a_)

    def adjust_offset(self, seq_b, adj_b=False, offset='kmmer', count=True, **kwarg):
        methoddict = {'kmmer': self.kmmer_loop,}
        func = methoddict.get(offset, self.kmmer_loop)
        brep = seq_b.rep_seq(count=count) if isinstance(
            seq_b, Alignment) else seq_b
        if sum(self.count) >= sum(seq_b.count) or adj_b:
            index = func(self.rep_seq(count=count), brep, **kwarg)
            seq_b = seq_b.copy()
            seq_b._offset(index)
            return self, seq_b
        else:
            index = func(brep, self.rep_seq(count=count), **kwarg)
            seq_a = self.copy()
            seq_a._offset(index)
            return seq_a, seq_b

    def kmmer_loop(self, a, b, k=4, dis=False,**kwargs):
        def kmmer(a, b, k):
            """
            a is shorter than b
            """
            match = 0
            for i in range(k, len(a)+1):
                # match += int(a[i-k:i] in b[i-k:i+4])
                match += int(a[i-k:i] == b[i-k:i])
            return match
        flip = False
        _a = a.replace('-', '')
        _b = b.replace('-', '')
        if len(_a) > len(_b):
            _a, _b = _b, _a
            flip = True
        result = np.zeros(len(_b), float)
        for i in range(len(_b)):
            result[i] = kmmer(_a, _b[i:]+_b[0:i], k)
        index = result.argmax()
        if dis:
            length = len(_a)
            k1 = 1-kmmer(_a,_b[index:]+_b[0:index],k-1)/(length-k+2)
            k2 = 1-kmmer(_a,_b[index:]+_b[0:index],k+1)/(length-k)
            k3 = 1-result.max()/(length-k+1)
            return (k1*k2*k3)**(1/3)
        else:
            if flip:
                index = 0 if len(_b)-index >= len(_a) else len(_b)-index
            return self._index_backcal(a, b, index)

    def hybrid_distance(self, b,k=4,count=True,**kwargs):
        a=self.rep_seq(count)
        b=b if isinstance(b,str) else b.rep_seq(count)
        k = self.kmmer_loop(b, a, k=k, dis=True)
        return k

    def nw_distance(self,align,gap=4, gapext=1, offset=True, name=None, count=True,**kwargs):
        if not isinstance(align, Alignment):
            align = Alignment(align)
        return self.align(align,gap, gapext, offset, name, count,nw_distance=True,**kwargs)

    def _nw_distance(self,align,count=True,threshold=0.8,window=5):
        """
        calculate distance between self and another alignment. they must be the already aligned alignments.
        threshold is the minimum probability for a sequence to be considerred continuous chunck.
        window is the minimum chunck of sequence to grant full score.
        """
        m = np.zeros_like(self.similarity_matrix,float)
        np.fill_diagonal(m,1.0)
        a = np.array(self._freq(count))
        b = np.array(align._freq(count))
        score_array = np.sum(np.matmul(np.reshape(a, (-1, 5, 1)), np.reshape(b, (-1, 1, 5)))*m,axis=(1,2))
        max_score = len(score_array)
        score = np.sum(self._window_scan(threshold,window,score_array,penalty=0.5))
        return 1-score/max_score

    def _window_scan(self,threshold,window,score_array,penalty=0.1):
        """
        give score array a penalty if the chunck is less than window size.
        """
        adjust_array=np.zeros_like(score_array)
        count = 0
        for i,j in enumerate(score_array):
            if j<threshold:
                adjust_array[i]=penalty
                if count>0:
                    if count >= window:
                        adjust_array[i-count:i]=1#penalty+min(window,count)*(1-penalty)/window
                    else:
                        adjust_array[i-count:i]=penalty
                    count=0
            else:
                count+=1
        if count>0:
            if count >= window:
                adjust_array[i-count+1:i+1]=1#penalty+min(window,count)*(1-penalty)/window
            else:
                adjust_array[i-count+1:i+1]=penalty
            # adjust_array[i+1-count:i+1]=penalty+min(window,count)*(1-penalty)/window
        return score_array*adjust_array

    def distances(self,method):
        """
        wrapper for distances functions.
        method =
        """
        if method == 'hybrid_distance':
            return self.hybrid_distance
        elif method == 'nw_distance':
            return self.nw_distance
        elif method == 'sw_distance':
            return self.sw_distance
        elif method == 'lev_distance':
            return self._lev_distance
        else:
            raise KeyError('Unrecognized distance method.')

    def _lev_distance(self, b, count=True,offset=False,**kwargs):
        if offset:
            b = Alignment(b) if isinstance(b, str) else b
            a, b = self.adjust_offset(b, offset=offset, count=count,**kwargs)
            a,b = a.rep_seq(count),b.rep_seq(count)
        else:
            a = self.rep_seq(count)
            b = b if isinstance(b,str) else b.rep_seq(count)
        a = a.replace('-', '')
        b = b.replace('-', '')
        dis = lev_distance(a, b,threshold=kwargs.get('threshold',100))
        return dis

    def _offset(self, index):
        new_offset = [0]*len(self.offset)
        for k, (i, j) in enumerate(zip(self.seq, self.offset)):
            lenth = len(i) - i.count('-')
            offset = index - i[:index].count('-')
            new_offset[k] = (j+offset) % lenth
        self.offset = new_offset
        # self.offset = [index]*len(self.seq)
        self.seq = [i[index:]+i[0:index] for i in self.seq]
        self.freq = self.freq[index:]+self.freq[0:index]

    def sw_distance(self, b, gap=4, gapext=1, offset=False, count=True,**kwargs):
        """
        cal the sw distance of current aligment to a given alignment. if offset =Ture,
        will try to rotate b for optimal kmer match or sw match based on offset method.
        offset can be sw or kmmer.
        """
        b = Alignment(b) if isinstance(b, str) else b
        if offset:
            a, b = self.adjust_offset(b, adj_b=True, offset=offset)
        else:
            a = self
        a = np.reshape(np.array(a._freq(count)), (-1, 5, 1))
        b = np.reshape(np.array(b._freq(count)), (-1, 1, 5))
        max_score = np.sum(np.matmul(a, a.reshape(-1, 1, 5))
                           * self.similarity_matrix)
        H = np.zeros((len(a) + 1, len(b) + 1), float)
        for i, j in product(range(1, H.shape[0]), range(1, H.shape[1])):
            score = np.sum(np.matmul(a[i-1], b[j - 1])
                           * self.similarity_matrix)
            match = H[i - 1, j - 1] + score
            delete = max(H[i - k-1, j] - gap - k*gapext for k in range(i))
            insert = max(H[i, j - k-1] - gap-k*gapext for k in range(j))
            H[i, j] = max(match, delete, insert, 0)
        s = 1-np.max(H)/max_score
        return s

    # alignment txt tools:
    def correlation(self,position=[1,2],save=False,show=True):
        """
        show contigency table of 2 positions of a target alignment.
        caution: the index is 1 based, first position is 1
        """
        align = self
        i,j=position
        J1_1= align[i-1][0]
        J1_2 = align[j-1][0]
        df = pd.crosstab(pd.Series(J1_1,name='pos'+str(i)+'\\'+'pos'+str(j)),pd.Series(J1_2,name='pos'+str(j)))
        total = df.sum().sum()
        df['col_sum']=df.sum(axis=1)
        df.loc['row_sum',:]=df.sum(axis=0)
        df2 = df.apply(lambda x:x/total)
        df = pd.concat([df,df2],axis=1)
        df[''.join(['T.Co.',str(i),'=>',str(j)])]=[theils_u(J1_2,J1_1)]+['']*(len(df.index)-1)
        df[''.join(['T.Co.',str(j),'=>',str(i)])]=[theils_u(J1_1,J1_2)]+['']*(len(df.index)-1)
        if save:
            save = save if isinstance(save,str) else 'CorM_'+self.name+'_N'+str(i)+'_N'+str(j)+'.csv'
            df.to_csv(save)
        if show:
            print(repr(df))
        return df

    # alignment plots:
    def dna_logo(self, save=False, show=True, count=True,ax=None):
        freq = np.array(self._freq(count))
        en = 2.88539008/max(sum(self.count),1.5)
        info = (np.log(5)/np.log(2)-en-self.entropy(count=count))
        if np.min(info) < 0:
            info -= np.min(info)
        height = (freq.T*info).T
        order = ['A', 'G', 'C', 'T', '-']
        height = [sorted(list(zip(order, i)), key=lambda x:x[1])
                  for i in height]
        fp = FontProperties(family="monospace", weight="bold")
        LETTERS = {"T": TextPath((-0.395, 0), "T", size=1.35, prop=fp),
                   "G": TextPath((-0.395, 0), "G", size=1.35, prop=fp),
                   "A": TextPath((-0.395, 0), "A", size=1.35, prop=fp),
                   "C": TextPath((-0.395, 0), "C", size=1.35, prop=fp),
                   "-": TextPath((-0.395, 0), "I", size=1.35, prop=fp)}
        COLOR_SCHEME = {'G': 'orange',
                        'A': 'red',
                        'C': 'blue',
                        'T': 'darkgreen',
                        '-': 'black'}
        if ax:
            ax = ax
            drawx=False
        else:
            fig, ax = plt.subplots(figsize=(7, 2))
            drawx=True
        for x, scores in enumerate(height):
            y = 0
            for letter, score in scores:
                text = LETTERS[letter]
                t = mpl.transforms.Affine2D().scale(1.2, score) + \
                    mpl.transforms.Affine2D().translate(x+1, y) + ax.transData
                p = PathPatch(
                    text, lw=0, fc=COLOR_SCHEME[letter],  transform=t)
                ax.add_artist(p)
                y += score
        x_tick_label = ([str(k + 1) + '\n' + i[-1][0] for k, i in enumerate(height)]
                            if drawx else [str(k + 1) for k, i in enumerate(height)])
        ax.set_title('{} Total count: {}'.format(str(self.name),sum(self.count)),fontsize=6)
        ax.set_xticks(range(1, len(height)+1), )
        ax.set_xticklabels(x_tick_label)
        ax.set_xlim((0, len(height)+1))
        ax.set_ylim((0, 2.33))
        ax.tick_params(axis='both', which='both', labelsize=6)
        if save:
            plt.tight_layout()
            save = save if isinstance(
                save, str) else str(self.name)+'_logo.svg'
            plt.savefig(str(save),dpi=150)
        if show:
            plt.tight_layout()
            plt.show()

    def plot_correlation(self,save=False,**kwargs):
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
        align=self
        dataset = np.array([align[i][0] for i in range(len(align))]).T
        dataset=pd.DataFrame(dataset,columns=range(1,(dataset.shape[1]+1)))
        _=associations(dataset=dataset,**kwargs)
        if save:
            _save = save if isinstance(save,str) else 'CorM'+self.name+'.svg'
            plt.savefig(_save)
            plt.clf()
        else:
            plt.show()
        if kwargs.get('return_results',False):
            return _


    # to plot strucutre from rep sequence:
    # def to_structure(self,count=True):
    #     saveloc=getattr(self,'save_loc',None)
    #     return Structure(sequence=self.rep_seq(count=count).replace('-',''),name=self.name,save_loc=saveloc)




class Node():
    def __init__(self, i, j, a, b, gap=0):
        self.index = (i, j)
        self.a = a
        self.b = b
        self.gap = gap

    def __len__(self):
        return len(self.a)

    def add_children(self, index, direction, seq_a, seq_b):
        i, j = index
        new = []
        a_gap = 0 if self.a.endswith(('I','-')) or len(self.a) == 0 else 1
        b_gap = 0 if self.b.endswith(('I','-')) or len(self.b) == 0 else 1
        diagonally = direction//100000
        leftward = direction//1000 % 1000
        upward = direction % 1000
        if diagonally: # if trace go diagonally
            a = self.a.copy().append(seq_a[i-1])
            b = self.b.copy().append(seq_b[j-1])
            gap = self.gap
            new.append(Node(i-1, j-1, a=a, b=b, gap=gap))
        if leftward: # if trace go to left
            a = self.a.copy().append('I'*leftward)#*(j!=1 or i!=1)
            l_slice = j-leftward-1 if j-leftward-1 >=0 else None
            b = self.b.copy().append(seq_b[j-1:l_slice:-1])
            gap = self.gap+a_gap
            new.append(Node(i, j-leftward, a=a, b=b, gap=gap))
        if upward: # if trace go upwards.
            u_slice = i-upward-1 if i-upward-1 >=0 else None
            a = self.a.copy().append(seq_a[i-1:u_slice:-1])
            b = self.b.copy().append('I'*upward)
            gap = self.gap+b_gap
            new.append(Node(i-upward, j, a=a, b=b, gap=gap))
        return new

    def qc(self):
        result = self.gap
        if self.a.endswith('I') or self.b.endswith('I'):
            result -= 1
        return result
##############################################################################


##############################################################################
# nominal correlation calculation and plotting modules

def conditional_entropy(x, y):
    """
    Calculates the conditional entropy of x given y: S(x|y)

    Wikipedia: https://en.wikipedia.org/wiki/Conditional_entropy

    :param x: list / NumPy ndarray / Pandas Series
        A sequence of measurements
    :param y: list / NumPy ndarray / Pandas Series
        A sequence of measurements
    :return: float
    """
    # entropy of x given y
    y_counter = Counter(y)
    xy_counter = Counter(list(zip(x,y)))
    total_occurrences = sum(y_counter.values())
    entropy = 0.0
    for xy in xy_counter.keys():
        p_xy = xy_counter[xy] / total_occurrences
        p_y = y_counter[xy[1]] / total_occurrences
        entropy += p_xy * np.log(p_y/p_xy)
    return entropy

def cramers_v(x, y):
    """
    Calculates Cramer's V statistic for categorical-categorical association.
    Uses correction from Bergsma and Wicher, Journal of the Korean Statistical Society 42 (2013): 323-328.
    This is a symmetric coefficient: V(x,y) = V(y,x)

    Original function taken from: https://stackoverflow.com/a/46498792/5863503
    Wikipedia: https://en.wikipedia.org/wiki/Cram%C3%A9r%27s_V

    :param x: list / NumPy ndarray / Pandas Series
        A sequence of categorical measurements
    :param y: list / NumPy ndarray / Pandas Series
        A sequence of categorical measurements
    :return: float
        in the range of [0,1]
    """
    confusion_matrix = pd.crosstab(x,y)
    chi2 = ss.chi2_contingency(confusion_matrix)[0]
    n = confusion_matrix.sum().sum()
    phi2 = chi2/n
    r,k = confusion_matrix.shape
    phi2corr = max(0, phi2-((k-1)*(r-1))/(n-1))
    rcorr = r-((r-1)**2)/(n-1)
    kcorr = k-((k-1)**2)/(n-1)
    return np.sqrt(phi2corr/min((kcorr-1),(rcorr-1)))

def theils_u(x, y):
    """
    Calculates Theil's U statistic (Uncertainty coefficient) for categorical-categorical association.
    This is the uncertainty of x given y: value is on the range of [0,1] - where 0 means y provides no information about
    x, and 1 means y provides full information about x.
    This is an asymmetric coefficient: U(x,y) != U(y,x)

    Wikipedia: https://en.wikipedia.org/wiki/Uncertainty_coefficient

    :param x: list / NumPy ndarray / Pandas Series
        A sequence of categorical measurements
    :param y: list / NumPy ndarray / Pandas Series
        A sequence of categorical measurements
    :return: float
        in the range of [0,1]
    """
    s_xy = conditional_entropy(x,y)
    x_counter = Counter(x)
    y_counter = Counter(y)
    total_occurrences = sum(x_counter.values())
    # this is to remove high insertion positions.
    if x_counter.get('-',0)/total_occurrences>0.2 or y_counter.get('-',0)/total_occurrences>0.2:
        return 0
    p_x = list(map(lambda n: n/total_occurrences, x_counter.values()))
    # p_y = list(map(lambda n: n/total_occurrences, y_counter.values()))
    s_x = ss.entropy(p_x)
    # s_y = ss.entropy(p_y)
    # max_entropy = math.log(len(p_x))
    # may_entropy = math.log(len(p_y))
    if s_x==0:#(s_x <= 0.05*max_entropy) or (s_y <= 0.05*may_entropy)
        return 0
    else:
        return (s_x - s_xy) / s_x

def associations(dataset, theil_u=True, plot=True,return_results = False, **kwargs):
    """
    input dataset is data frame
    Calculate the correlation/strength-of-association of features in data-set with both categorical (eda_tools) and
    continuous features using:
     - Cramer's V or Theil's U for categorical-categorical cases
    :param theil_u: Boolean (default: False)
        In the case of categorical-categorical feaures, use Theil's U instead of Cramer's V
    :param return_results: Boolean (default: False)
        If True, the function will return a Pandas DataFrame of the computed associations
    """
    columns = dataset.columns
    corr = pd.DataFrame(index=columns, columns=columns)
    for i in range(0,len(columns)):
        for j in range(i,len(columns)):
            if i == j:
                corr[columns[i]][columns[j]] = 1.0
            else:
                if theil_u:
                    corr[columns[j]][columns[i]] = theils_u(dataset[columns[i]],dataset[columns[j]])
                    corr[columns[i]][columns[j]] = theils_u(dataset[columns[j]],dataset[columns[i]])
                else:
                    cell = cramers_v(dataset[columns[i]],dataset[columns[j]])
                    corr[columns[i]][columns[j]] = cell
                    corr[columns[j]][columns[i]] = cell

    corr.fillna(value=np.nan, inplace=True)
    corr=corr.reindex(index=corr.index[::-1])
    annot= corr*10 if kwargs.get('annot',False) else False
    if plot:
        plt.figure(figsize=kwargs.get('figsize',(10,8)))
        sns.heatmap(corr, annot=annot,cmap=kwargs.get('cmap',None),linewidths=kwargs.get('linewidth',0),
                    fmt=kwargs.get('fmt','.0f'),xticklabels=1,yticklabels=1,square=True)#,cmap='YlGnBu'
    if return_results:
        return corr

##############################################################################


def buildMSA(sequence,name,**kwargs):
    """
    give a dict of sequence and alignment paramters, build an alignment object.
    kwargs: alignment parameters gap, gapext,
    simple align method.
    """
    gap=kwargs.get('gap',4)
    gapext=kwargs.get('gatext',2)
    offset=kwargs.get('offset',False)
    order=kwargs.get('order',True)
    if order:
        sequence = sorted(sequence, key=len,reverse=True)
    result=Alignment(sequence[0],name=name)
    for i in sequence[1:]:
        result=result.align(Alignment(i),name=name,offset=offset,gap=gap,gapext=gapext)
    return result
