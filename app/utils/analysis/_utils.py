# utility functions
"""
utility functions to be used in Alignment and Datareader classes.
"""
import os
import numpy as np
from itertools import combinations
from functools import partial
import multiprocessing
import datetime
from ._twig import Tree,Clade
from ._alignment import Alignment,lev_distance
import time
import tqdm
import psutil
import platform

ascii=True if platform.platform().startswith('Win') else None


        

def poolwrapper(task,workload,initializer=None,initargs=None,chunks=None,total=None,callback=None,progress_gap=(0,100),**kwargs):
    workerheads=psutil.cpu_count(logical=False)
    worker=multiprocessing.Pool(workerheads,initializer,initargs)
    total = total or len(workload)
    chunksize= int(total//chunks)+1 if chunks else 1
    result = []
    count=0
    progress = progress_gap[0]
    for _ in worker.imap(task, workload, chunksize):
        count+=1
        result.append(_) 
        if callback :
            current_pro = count/total*(progress_gap[1]-progress_gap[0])+progress_gap[0]
            if current_pro > progress + 1:
                progress = current_pro
                callback(current_pro)     
    worker.close()
    worker.join()
    worker.terminate()
    return result



def lev_cluster_from_seed(seed, list_of_seq, distance, connect):
    """
    give a list of seed and sequence,
    use the seed to cluster sequence.
    """
    seedresult = {i:[] for i in seed}
    id = os.getpid()
    print("Process {} started....{} tasks.".format(id,len(list_of_seq)))
   
    # percentcounter=0.05
    for i in list_of_seq:
        # if (k/length)>percentcounter:
        #     print("Process {}: {:.2f}% done...".format(id,percentcounter*100))
        #     percentcounter+=0.05
        for j in seed:
            dis = lev_distance(i, j,threshold=distance)
            if dis <= distance:
                seedresult[j].append(i)
                # break to avoid search all entrys
                break
    # print(seedresult)
    connect.put((id,seedresult))
    print("Process {} finished.".format(id))

def mapdistance(seq,seqlist,threshold,multithre=10000,showprogress=False):
    """
    return a list of distance of seq to each seq in seqlist.
    """
    discalc=partial(lev_distance,s2=seq,threshold=threshold)
    if len(seqlist)>multithre:
        distances=poolwrapper(discalc,seqlist,chunks=100,desc='MapDistance:',showprogress=showprogress)
        return distances
    else:
        return list(map(discalc,seqlist))

def lev_cluster(list_of_seq,apt_count, distance,cutoff=(35,45),clusterlimit=5000,findoptimal=False,callback=None):
    """
    cluster a list of sequence and its count, based on their levenstein distance, threshold is given by 'distance'
    will return a dictionary of lists.
    clusterlimit will limit cluster number to a threshold, after that, cluster number cannot grow, each new
    sequence is inserted to the existing cluster.
    """
   


    print('Start clustering with levenshtein distance...')
    print('Current time: {}'.format(datetime.datetime.now()))
    seq = dict(zip(list_of_seq,apt_count))
    list_of_seq = [i for i in list_of_seq if cutoff[0]<=len(i)<=cutoff[1]]
    result_key = [list_of_seq[0]]
    result = {list_of_seq[0]: []}
    lenth = len(list_of_seq)
    percentcounter=0
    current=0
    starttime=time.time()
    for k,i in enumerate(list_of_seq):
        if callback: 
            current = k/lenth*80
            if percentcounter  < current -1:
                percentcounter = current
                callback(current)
        if len(result_key)>clusterlimit:
            print('Cluster limit of {} reached. Start seed clustering...'.format(clusterlimit))
            break
        temp = i
        if findoptimal:
            distlist = mapdistance(i,result_key,distance)
            if min(distlist)<=distance:
                temp = result_key[distlist.index(min(distlist))]
        else:
            for j in result_key:
                dis = lev_distance(i, j,threshold=distance)
                if dis <= distance:
                    temp = j
                    break
                    # break to avoid search all entrys
        if temp == i:
            result_key.append(i)
            result.update({i: [i]})
        else:
            result[temp].append(i)
    stop_sum_count=[0,0] # to record the read number of starting sequence when cluster ceased.
    if k < len(list_of_seq)-1:
        stop_sum_count[0]=k-1
        stop_sum_count[1]=apt_count[k-1]
        processnumber = psutil.cpu_count(logical = False)
        remaining=list_of_seq[k:]
        segment = len(remaining)//processnumber+1
        segments=[remaining[i*segment:(i+1)*segment] for i in range(processnumber)]
        quene = multiprocessing.Queue()
        process = []
        for i in range(processnumber):
            args=(result_key,segments[i],distance,quene)
            _=multiprocessing.Process(target=lev_cluster_from_seed,args=args)
            process.append(_)
            _.start()
        seedresult_list=[]
        # to avoid dead lock, fetch queue every 60s while process is active.
        process_c = (80-current)/processnumber
        cyclecount=0
        while any([i.is_alive() for i in process]):
            while not quene.empty():
                _,r=quene.get()
                print('Process {} result received.'.format(_))
                seedresult_list.append(r)
                current=current+process_c
                cyclecount=0
            callback(current+(process_c)*cyclecount/(300+cyclecount) )
            time.sleep(1)
            cyclecount+=1
        time.sleep(1)
        while not quene.empty():
            _,r=quene.get()
            print('Process {} result received.'.format(_))
            seedresult_list.append(r)
        for i in process:
            i.join()
            i.terminate()
        for seedresult in seedresult_list:
            for i,j in seedresult.items():
                result[i].extend(j)
    new_result = {}
    counter_=1
    for k,i in sorted(result.items(),key=lambda x:sum([seq[i] for i in x[1]]),reverse=True):
        sort_list = sorted([(k,seq[k]) for k in i],key=lambda x:x[1],reverse=True)
        new_result.update({'C'+str(counter_):sort_list})
        counter_+=1
    callback(80)
    print('Cluster done. Time elapsed: {:.2f}s.'.format(time.time()-starttime))
    return new_result, stop_sum_count


##############################################################################
# build tree and aligning
# @registor_function
def distance_calculator(x,kwargs):
    if kwargs.get('distance','hybrid_distance')=='hybrid_distance':
        return x[1].hybrid_distance(x[0],**kwargs)
    elif kwargs.get('distance')=='nw_distance':
        return x[0].nw_distance(x[1],**kwargs)

# @registor_function
def build_distance_matrix(list_of_alignment,**kwargs):
    print('Start building distance matrix...')
    print('Current time: {}'.format(datetime.datetime.now()))
    starttime=time.time()
    n = len(list_of_alignment)
    total=n*(n-1)/2
    print('Matrix Size: {} X {}.'.format(n,n))
    print('ETA: {:.2f} minutes...'.format(total*6.17172e-06))
    wrapper = partial(distance_calculator,kwargs=kwargs)
    z=poolwrapper(wrapper,combinations(list_of_alignment,2),chunks=100,total=int(total),desc='Build Matrix:',showprogress=True)
    dm = np.zeros((n,n),float)
    for i in range(n-1):
        for j in range(i+1,n):
            index = int((2*n-2-i)*(i+1)/2-(n-1-j)-1)
            dm[i,j]=dm[j,i]=z[index]
    print('Build distance matrix done. Elapsed time: {:.2f}s'.format(time.time()-starttime))
    return dm

# @registor_function
def build_distance_matrix_single_process(list_of_alignment,**kwargs):
    print('Start building distance matrix...')
    n = len(list_of_alignment)
    dm = np.zeros((n,n),float)
    lenth = n**2/2
    if kwargs.get('distance','hybrid_distance')=='hybrid_distance':
        wrapper = lambda x:x[0].hybrid_distance(x[1],**kwargs)
    elif kwargs.get('distance')=='nw_distance':
        wrapper = lambda x:x[0].nw_distance(x[1],**kwargs)
    for i in range(1,n):
        for j in range(i):
            p = i**2/2 +j
            if p%1000 ==0:
                print('Building matrix {:.3f}% done.'.format(p/lenth*100))
            score = wrapper((list_of_alignment[i],list_of_alignment[j]))
            dm[i,j] = dm[j,i]=score
    print('Build distance matrix done.')
    return dm

# @registor_function
def neighbor_join(dm,name_list,list_align,record_path=False,offset=True,count=True,gap=7,gapext=2,**kwargs):
    """
    construct from distance matrix and name_list.
    """
    print('Start building tree and align...')
    starttime=time.time()
    clades = [Clade(None, name) for name in name_list]
    inner_count = 0
    lenth = len(dm)
    if record_path:
        dict_align = dict(zip(name_list,list_align))
    while len(dm) > 2:
        dm_sum = np.sum(dm,axis=0)/(len(dm) -2)
        new_dm = dm -  dm_sum - dm_sum[:,None]
        np.fill_diagonal(new_dm,0)
        # adjust_array = np.tril(np.full(new_dm.shape,1.00001),-1) (possible way to avoid full zero array.)
        new_dm=np.tril(new_dm,1)#+adjust_array
        min_i,min_j = np.unravel_index(new_dm.argmin(),new_dm.shape)
        if min_i==min_j:min_i+=1 # this is when full zero dm_new, shift joining to 0 and 1.
        clade1 = clades[min_i]
        clade2 = clades[min_j]
        inner_count += 1
        temp_name =  "J" + str(inner_count) if record_path else None
        inner_clade = Clade(None,temp_name)
        inner_clade.clades.append(clade1)
        inner_clade.clades.append(clade2)
        clade1.parent=clade2.parent = inner_clade
        # assign branch length
        clade1.branch_length = (dm[min_i, min_j] + (dm_sum[min_i] -
                                dm_sum[min_j])) / 2.0
        clade2.branch_length = dm[min_i, min_j] - clade1.branch_length
        align_temp = list_align[min_j].align(list_align[min_i],name=temp_name ,offset=offset,gap=gap,gapext=gapext,count=count,**kwargs)
        if record_path:
            dict_align.update({temp_name:align_temp})
        list_align[min_j]=align_temp
        # update node list
        clades[min_j] = inner_clade
        del clades[min_i]
        del list_align[min_i]
        # rebuild distance matrix,
        # set the distances of new node at the index of min_j
        for k in range(0, len(dm)):
            if k != min_i and k != min_j:
                dm[k, min_j] = dm[min_j, k] = (dm[min_i, k] + dm[min_j, k] -
                                dm[min_i, min_j]) / 2.0
        dm = np.delete(dm,min_i,axis=0)
        dm = np.delete(dm,min_i,axis=1)
    # set the last clade as one of the child of the inner_clade
    root = None
    if lenth >2:

        if clades[0] == inner_clade:
            clades[0].branch_length = 0
            clades[1].branch_length = dm[1, 0]
            clades[0].clades.append(clades[1])
            clades[1].parent=clades[0]
            root = clades[0]

        else:
            clades[0].branch_length = dm[1, 0]
            clades[1].branch_length = 0
            clades[1].clades.append(clades[0])
            clades[0].parent=clades[1]
            root = clades[1]

    elif lenth==2:
        clades[0].branch_length = 0.2
        clades[1].branch_length = 0.2
        clades[0].clades.append(clades[1])
        clades[1].parent=clades[0]
        root = clades[0]
    else:
        clades[0].branch_length = 0.2
        root = clades[0]
    if record_path:
        if lenth>=2:
            dict_align.update({root.name:list_align[0].align(list_align[1],name='root',offset=offset,gap=gap,gapext=gapext,count=count,**kwargs)})
    else:
        dict_align = list_align[0].align(list_align[1],offset=offset,gap=gap,gapext=gapext,count=count,**kwargs)
    print('Build tree and align done. Elapsed time: {:.2f}s.'.format(time.time()-starttime))
    return Tree(root, rooted=False,name='root'),dict_align

# @registor_function
def align_clustered_seq_with_CLUSTAL(data,offset=True,k=4,count=True,gap=7,gapext=2,**kwargs):
    """
    data is a dict of lev clustered sequence with counts
    (old method, building tree and align within cluster. it is not necessary.)
    """
    cluster = dict.fromkeys(data)
    w = len(cluster.keys())
    data = list(data.items())
    for p,(key,value) in enumerate(data):
        if p%100==0:
            print("In cluster alignment: {:.2f}% done.".format(p/w*100))
        if len(value)==1:
            cluster[key]=Alignment(*value[0][:2],name=key)
        elif len(value)==2:
            cluster[key]=Alignment(*value[0][:2]).align(Alignment(*value[1][:2]),name=key)
        else:
            name_list = [k for i,j,k in value]
            list_align = [Alignment(*i[:2]) for i in value]
            dm = build_distance_matrix(list_align,k=k,count=count)
            _,root = neighbor_join(dm,name_list,list_align,offset=offset,k=k,count=count,gap=gap,gapext=gapext)
            root.name=key
            cluster[key]=root
    return cluster

# @registor_function
def align_clustered_seq(data,**kwargs):
    """
    kwargs: offset=True,k=4,count=True,gap=5,gapext=1
    data is a dict of lev clustered sequence with counts.
    data={'C1':[['ATCG', count,id],[]]}
    return dict with Alignments. {'C1': AlignmentC1}
    """
    cluster = dict.fromkeys(data)
    # w = len(cluster.keys())
    data = list(data.items())
    # print("Starting in cluster align ...")
    # print('Current time: {}'.format(datetime.datetime.now()))
    # percentcounter=0.05
    starttime=time.time()
    callback=kwargs.pop('callback')
    wrapper = partial(_cluster_align,kwargs=kwargs)
    z=poolwrapper(wrapper,data,callback=callback,progress_gap=(80,95))
    cluster = dict(z)
    # print("In cluster alignment finished. Time Elapsed: {:.2f}s.".format(time.time()-starttime))
    return cluster


def _cluster_align(item,kwargs):
    key,value=item
    temp=Alignment(*value[0][:2])
    rest=sorted(value[1:],key=lambda x:(lev_distance(value[0][0],x[0]),len(x[0])))
    for i in rest:
        temp=temp.align(Alignment(*i[:2]),**kwargs)
    temp.name=key
    return (key,temp)

##############################################################################
