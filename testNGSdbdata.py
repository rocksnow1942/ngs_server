from itertools import islice
import os

def reverse_comp(s):
    s=s.upper()
    comp=''.join(map(lambda x:dict(zip('ATCGN','TAGCN'))[x]  ,s))
    return comp[::-1]

def check_file_reverse_comp(f1,f2):
    nonrevcount = 0
    for l1,l2 in islice(zip(f1,f2),1,800,4):
        l1_ = l1.decode('utf-8')
        l2_=l2.decode('utf-8')
        if reverse_comp(l1_.strip())!=l2_.strip():
            nonrevcount+=1
    if nonrevcount>50:
        return False
    return True



def file_blocks(files, size=65536):
    while True:
        b = files.read(size)
        if not b: break
        yield b


def file_generator(f1,f2):
    with open(f1,'rt') as f, open(f2,'rt') as r:
        for line,rev in zip(islice(f,1,None,4),islice(r,1,None,4)):
            line=line.strip()
            rev=rev.strip()

            yield line,rev

def file_generator_raw(f1,f2):
    with open(f1,'rt') as f, open(f2,'rt') as r:
        for line,rev in zip(islice(f,1,None),islice(r,1,None)):
            line=line.strip()
            rev=rev.strip()
            yield line,rev

def totalread(f1):
    with open(f1, 'rt') as f:
        fb1 = file_blocks(f)
        totalread = sum(bl.count("\n") for bl in fb1)
    return totalread/4

totalread(f)
totalread(r)

f="/Users/hui/Downloads/N8A-C-R8CDF_S1_L001_R1_001.fastq"
r="/Users/hui/Downloads/N8A-C-R8CDF_S1_L001_R2_001.fastq"

fg = file_generator_raw(f,r)

fgs = file_generator(f,r)
len(itfp)

count = 0
revcomp = 0
for i in range(100):
    l1,l2 = next(fgs)
    l2r = reverse_comp(l2)
    itfpindex = (itfp in l1) and l1.index(itfp)
    krpcindex = (krpc in l1) and l1.index(krpc)
    itfpindex1 = (itfp in l2r) and l2r.index(itfp)
    krpcindex1 = (krpc in l2r) and l2r.index(krpc)
    Fstrand = l1[itfpindex+len(itfp):krpcindex]
    Rstrandrc = l2r[itfpindex1+len(itfp):krpcindex1]
    print(Fstrand)
    print(Rstrandrc)
    print('+++++++++++'*3)
    # if not itfpindex:
    #     count += 1
    #     l1_p = l1[2:10]
    #     if reverse_comp(l1_p) not in l2r:
    #         revcomp +=1



count/1000

revcomp/1000


    #     print(l1)
    # print("S{:>3d}; Forward F {} ; R {}".format(i,itfpindex,krpcindex))
    # print("S{:>3d}; Reverse F {} ; R {}".format(i,itfpindex1,krpcindex1))


for i in range(80):
    l1,l2=next(fg)
    print(l1+'\n'+l2)


a=(next(fg))


from itertools import islice,zip_longest

for i in zip_longest([1,2],[]):
    print(i)
tuple(i for i in range(4))
f1 = "/Users/hui/Desktop/exp46_30-217785519/20190412_S1_R1_001.fastq"
f2 = "/Users/hui/Desktop/exp46_30-217785519/20190412_S1_R2_001.fastq"

def fgen(f1,f2):
    f= open(f1,'rt')
    for fw,fs,  in zip(islice(f, 1, None, 2), islice(f, 1, None, 2), ):
        fw=fw.strip()
            # if line == reverse_comp(rev):
               # self.revcomp+=1
        yield fw,fs
    f.close()
g = fgen(f1,f2)
for _ in g:
    continue
_

for i in zip_longest(islice([1,2,3],1,None,1),islice([],1,None,1)):
    print(i)


next(g)


a='a'
b=None

if a or b:
    print(a,b)
else:
    print('here')


from collections import Counter

a = Counter()

a['a']=3
a['b']=2
a['c']=5
a.most_common(100)


"{:<9}".format(4)

from datetime import datetime
datetime.now().strftime('%Y/%m/%d %H:%M')

from inspect import signature


class Test():
    pass

def test(a:int) -> str:
    return 0


str(signature(test))

Another = lambda x:print('haha')

def test(func):
    func(1)

test()

eval('test(Another)')


/Users/hui/Downloads/Exp63_S1_L001_R1_001.fastq.gz
/Users/hui/Downloads/Exp63_S1_L001_R2_001.fastq.gz

'/Users/hui/Downloads/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R1.fastq'

/Users/hui/Downloads/N8A-C-R8CDF_S1_L001_R1_001.fastq.gz
/Users/hui/Downloads/N8A-C-R8CDF_S1_L001_R2_001.fastq.gz
'/Users/hui/Downloads/N8A-C-R8CDF_S1_L001_R1_001.fastq'

import gzip

@time_func
def file_blocks(files, size=2**24): # read 16 MB data at 1 time.
    while True:
        b = files.read(size)
        if not b: break
        yield b
@time_func
def reader_obj(filename):
    if filename.endswith('.fastq'):
        return open(filename, 'rt')
    elif filename.endswith('.gz'):
        return gzip.open(filename, 'rt')
    else:
        return None
@time_func
def totalread(toread):
    with reader_obj(toread) as f:
        fb1 = file_blocks(f)
        totalread = sum(bl.count("\n") for bl in fb1)
    return totalread//4

totalread('/home/hui/ngs_server/app/cache/ngs_data_upload/Exp63_S1_L001_R2_001.fastq_20191112_154750-2.gz')

totalread('/home/hui/ngs_server/app/cache/ngs_data_upload/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R2.fastq')


def time_func(func):
    import time
    from inspect import signature
    sig=signature(func)
    def wrapped(*args,**kwargs):

        t1 = time.time()
        result = func(*args,**kwargs)
        t2 = time.time()

        print('Run {}: {:.5f}s; para:{}{}'.format(func.__name__,t2-t1,args,kwargs))
        return result
    wrapped.__signature__ = sig
    wrapped.__name__ = func.__name__
    return wrapped



def break_fastq_file(file,lines,tosave):
    with open(file,'rt') as f, open(tosave,'wt') as t:
        for i in range(lines*4):
            t.write(f.readline())

file1 = '/home/hui/ngs_server/app/cache/ngs_data_upload/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R1.fastq'
file2 = '/home/hui/ngs_server/app/cache/ngs_data_upload/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R2.fastq'

tosave1= '/home/hui/ngs_server/app/cache/ngs_data_upload/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R1s.fastq'
tosave2= '/home/hui/ngs_server/app/cache/ngs_data_upload/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R2s.fastq'
break_fastq_file(file1,100,tosave1)
break_fastq_file(file2,100,tosave2)

def reverse_comp(s):
    s=s.upper()
    comp=''.join(map(lambda x:dict(zip('ATCGN','TAGCN'))[x]  ,s))
    return comp[::-1]

def rc(s):
    s=s.upper().strip()
    d = {'A':'T','T':'A','C':'G','G':'C','N':'N'} #dict(zip('ATCGN','TAGCN'))
    comp = [d[i] for i in s[::-1]]
    return ''.join(comp)

seq="""TTAATGATTATCANTATTCTTCTTCGAGCCCTGAATTCGTCGCCCTCGTCCCATCTCGCGACCTTTTTTCGCGGTATATGAGTGGTCGCCACAGAGAAGAAACAAGACCAGCGATAGATTAAACTCAATACTCGTTGACGTCTAAAGATCGG"""

reverse_comp(seq)
seq2="TTAATGATTATCANTATTCTTCTTCGAGCCCTGAATTCGTCGCCCTCGTCCCATCTCGCGACCTT"
len(seq2)
def ft(func,para,number=1):
    import timeit
    def wrapper(func,para):
        def wrapped():
            if isinstance(para,dict):
                return func(**para)
            if isinstance(para,tuple):
                return func(*para)
            else:
                return func(para)
        return wrapped
    t = timeit.timeit(wrapper(func,para),number=number)
    print('Run {} {} times: {:.5f}s'.format(func.__name__,number,t))
    return t
len(seq)
ft(rc,seq,number=10000)
Run rc 10000 times: 0.16813s
0.16813064700181712

Run rc 10000 times: 0.10419s
0.1041855929979647


Run reverse_comp 10000 times: 1.32235s 152nt
1.3223510249990795

Run reverse_comp 10000 times: 0.51378s 65nt
0.5137808190011128
