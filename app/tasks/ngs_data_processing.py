from rq import get_current_job
from app import db
from app.models import models_table_name_dictionary, NGSSampleGroup, Primers, Rounds, Sequence, KnownSequence, Task, SeqRound, Analysis, generate_sample_info
from app import create_app
import os,gzip
from flask import current_app
from itertools import islice, zip_longest
from app.utils.ngs_util import reverse_comp, file_blocks, create_folder_if_not_exist
from collections import Counter
import re
from app.utils.analysis import DataReader
from app.utils.analysis._alignment import lev_distance
# from Levenshtein import distance as lev_distance
from functools import partial
from app.utils.analysis._utils import poolwrapper
from datetime import datetime
from inspect import signature

app = create_app(keeplog=False)
app.app_context().push()

class ProgressHandler():
    def __init__(self,):
        self.job = get_current_job()
        self.currentprogress = -1


    def __call__(self,progress,start=0,end=100):
        if self.job:
            progress = progress/100*(end-start) + start
            if progress - self.currentprogress> 0.2:
                task = Task.query.get(self.job.get_id())
                task.progress = round(progress,2)
                if progress >= 100:
                    task.complete = True
                db.session.commit()
                self.currentprogress = progress

_set_task_progress = ProgressHandler()

def illumina_nt_score(n):
    return """!"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHI""".index(n)

class NGS_Sample_Process:
    """
    process files into database commits. assuming files are already validated.
    possible filters: primer filter, F-R equal match filter, rev-comp filter, Q score filter, read filter
    filters: [F-R equal match length filter, rev-comp filter, Qscore filter; Qscore threshold, read threshold filter]
    """

    def __init__(self, f1, f2, sampleinfo,filters):
        self.f1 = f1
        self.f2 = f2
        self.sampleinfo = sampleinfo
        self.sampleinfo_rc = []
        for i in self.sampleinfo:
            self.sampleinfo_rc.append((reverse_comp(i[2]),reverse_comp(i[1]),reverse_comp(i[4]),reverse_comp(i[3])))


        self.filters = filters
        *_,self.score_threshold,self.commit_threshold = filters
        self.collection = Counter()
        self.primer_collection=Counter() # log wrong primers
        self.index_collection=Counter() # log wrong index
        self.length_count=Counter() # log sequence length
        # self.commit_result = Counter() # log commit , key is (round_id, sequence)
        self.unique_commit = Counter() # log unique sequence commited count in round
        self.total_commit = Counter() # log total commit in rounds
        self.failure_collection = Counter()
        self.partial_failure_collection = Counter()
        self.failure = 0 # log other un explained.
        self.score_filter = 0
        self.length_filter = 0
        self.aberrant_primers = 0
        # self.total = 0 # total reads
        self.revcomp = 0 # passed rev comp reads
        self.success = 0 # find match primers in one strand
        self.pattern = [(re.compile(j+'[AGTCN]{0,2}'+l) , re.compile(m+'[AGTCN]{0,2}'+k) ) for i,j,k,l,m in self.sampleinfo]
        self.total = self.totalread()
        ngsprimer = [(i.name, i.sequence)
                     for i in Primers.query.filter_by(role='NGS').all()]
        # ngsprimer = ngsprimer + [(i,reverse_comp(j)) for i,j in ngsprimer]
        # samplengsprimer = {i[j] for i in self.sampleinfo for j in [1,2]}
        self.ngsprimer = ngsprimer #[i for i in ngsprimer if i[1] not in samplengsprimer]
        selectionprimer = [(i.name, i.sequence) for i in Primers.query.filter(
                    Primers.role.in_(('PD', 'SELEX'))).all()]
        selectionprimer = selectionprimer + [(i,reverse_comp(j)) for i,j in selectionprimer]
        # ssp = {i[j] for i in self.sampleinfo for j in [3,4] }
        self.selectionprimer = [
            i for i in selectionprimer]  # if i[1] not in ssp
        self.ks = {i.rep_seq:i.id for i in KnownSequence.query.all()}

    def filter_display(self):
        return " & ".join(i for i in ["Eq-Len"*bool(self.filters[0]),"Rev-Comp"*bool(self.filters[1]) ,
                f"Q-score>{self.score_threshold}"*bool(self.filters[2]) ,
                f"Count>{self.commit_threshold}"*bool(self.commit_threshold) ] if i)

    def reader_obj(self, filename):
        if filename.endswith('.fastq'):
            return open(filename, 'rt')
        elif filename.endswith('.gz'):
            return gzip.open(filename, 'rt')
        else:
            return None

    def file_generator(self):
        f= self.reader_obj(self.f1) if self.f1 else []
        r = self.reader_obj(self.f2) if self.f2 else []
        # fastq = [self.f1.endswith('.fastq')]*2 + [self.f2.endswith('.fastq')]*2
        for fw_fs_rev_rs in zip_longest(islice(f, 1, None, 2), islice(f, 1, None, 2), islice(r, 1, None, 2), islice(r, 1, None, 2)):
            fw_fs_rev_rs = tuple(i and i.strip() for i in fw_fs_rev_rs) #if k else i.decode().strip()
            yield fw_fs_rev_rs
        if self.f1: f.close()
        if self.f2: r.close()

    def _fr_equal_length_filter(self,f,r):
        if len(f) == len(r):
            self.length_filter += 1
            return f
        else:
            # print(f'F: {f}')
            # print(f'R: {r}')
            return False

    def _rev_comp_filter(self,f,r):
        if f == r:
            self.revcomp+=1
            return f
        else:
            # print(f'F: {f}')
            # print(f'R: {r}')
            return False

    def _q_score_filter(self, forward, forward_score, reverse, reverse_score):
        best_score_nts = [(f, fs) if fs >= rs else (r, rs) for f, fs, r, rs in zip_longest(
            forward, forward_score, reverse, reverse_score,fillvalue=-1)]
        if min([i[1] for i in best_score_nts]) >= self.score_threshold:
            self.score_filter += 1
            return "".join(i[0] for i in best_score_nts)
        else:
            return False

    def result_filter(self, fmatch,rmatch):
        forward, forward_score = fmatch or ['',[0]]
        reverse, reverse_score = rmatch or ['',[0]]
        fr_eq = self._fr_equal_length_filter(forward,reverse)
        rev_com = self._rev_comp_filter(forward,reverse)
        q_score = self._q_score_filter(forward, forward_score, reverse, reverse_score)
        filter_result = [r for r, f in zip((fr_eq, rev_com, q_score), self.filters) if f]
        if all(filter_result):
            if filter_result:
                return filter_result[-1] # the final result is after passing Q score filter, if it passes rev comp filter, the same sequence will pass q score.
            else:
                return forward or reverse
        else:
            return None

    def process_seq(self, fw_fs_rev_rs):
        nomatch = True
        fw, fs,rev,rs = fw_fs_rev_rs
        for (rdid,*(primers)),primers_rc, patterns in zip(self.sampleinfo,self.sampleinfo_rc,self.pattern):
            fmatch = fw and self.match_pattern(fw,primers,patterns,fs)
            rmatch =  rev and self.match_pattern(rev,primers_rc,patterns,rs)
            if rmatch:
                rmatch = (reverse_comp(rmatch[0]),rmatch[1][::-1]) # if reverse match found, make the found part reverse complement.
            if fmatch or rmatch:
                nomatch = False
                self.success+=1
                matchresult = self.result_filter(fmatch,rmatch)
                if matchresult:
                    self.collection[(rdid,matchresult)]+=1
                break
        if nomatch:
            self.log_unmatch(fw or rev)

    def match_pattern_slow(self,seq,primers,patterns,score):
        """
        using re match to search.
        """
        match = False
        if all([i in seq for i in primers]):
            ffind = patterns[0].search(seq)
            if ffind:
                findex = ffind.span()[1]
                rfind = list(patterns[1].finditer(seq))
                if rfind:
                    rindex = rfind[-1].span()[0]
                    match = seq[findex:rindex]
        if match:
            return match, [illumina_nt_score(i) for i in score[findex:rindex]]
        else:
            return None

    def match_pattern(self,seq,primers,patterns,score):
        match=False
        fpi,rpi,fp,rp = primers
        findex = seq.find(fpi+fp)
        rindex = seq.rfind(rp+rpi)
        if findex>-1 and rindex>-1:
            match = seq[findex+ len(fpi+fp):rindex]

        if match:
            # print(seq)
            # print("*"*(findex)+(fpi+fp[:-1])+"|"+match+"|"+rp[1:]+rpi)
            return match , [illumina_nt_score(i) for i in score[findex+ len(fpi+fp):rindex]]
        else:
            return None

    def log_unmatch(self,seq):
        """
        log sequence that is not matched.
        """
        ab = True
        toadd = []
        for n,p in self.selectionprimer:
            if p in seq:
                ab = False
                # self.primer_collection[n]+=1
                idx = seq.index(p)
                temp=None
                for n2, p2 in self.ngsprimer:
                    if p2 in seq[idx-3-len(p2): idx] :
                        temp = (n2, n)
                        # self.primer_collection[(n2,n)]+=1
                        break
                    elif (p2 in seq[idx+len(p):idx+len(p)+3 + len(p2)]):
                        temp = (n,n2)
                        # self.primer_collection[(n, n2)] += 1
                        break
                        # self.index_collection[n2]+=1
                if temp:
                    toadd.append(temp)
                    
                else:
                    toadd.append((n,None))
        if ab:
            self.failure+=1
            self.failure_collection[seq] += 1
        else:
            self.primer_collection[tuple(toadd)] += 1
            self.partial_failure_collection[seq] += 1
            self.aberrant_primers +=1

    def totalread(self):
        toread = self.f1 or self.f2
        with self.reader_obj(toread) as f:
            fb1 = file_blocks(f)
            totalread = sum(bl.count("\n") for bl in fb1)
        return totalread//4

    def commit(self, commit='true'):
        if commit =='true':
            for k in list(self.collection.keys()):
                rd_id,seq = k
                count = self.collection[k]
                if count > self.commit_threshold:  # only over 2 count sequence will be committed.
                    # self.collection.pop(k)
                    self.length_count[len(seq)]+=count
                    # self.commit_result[k]+=count
                    self.set_commit_result(rd_id, count)
                    sequence = Sequence.query.filter_by(aptamer_seq=seq).first()
                    if sequence:
                        seqround = SeqRound.query.filter_by(sequence=sequence,rounds_id=rd_id).first()
                        if seqround:
                            seqround.count += count
                        else:
                            seqround = SeqRound(sequence=sequence, rounds_id=rd_id, count=count)
                            db.session.add(seqround)
                    else:
                        sequence = Sequence(aptamer_seq=seq,known_sequence_id=self.ks.get(seq,None))
                        db.session.add(sequence)
                        seqround = SeqRound(sequence=sequence, rounds_id=rd_id, count=count)
                        db.session.add(seqround)
            db.session.commit()
        elif commit=='retract':
            for k in list(self.collection.keys()):
                rd_id, seq = k
                count = self.collection[k]
                if count > self.commit_threshold:
                    # self.collection.pop(k)
                    sequence = Sequence.query.filter_by(
                        aptamer_seq=seq).first()
                    seqround = SeqRound.query.filter_by(
                        sequence=sequence, rounds_id=rd_id).first()
                    if seqround:
                        seqround.count -= count
                        if seqround.count < 1:
                            db.session.delete(seqround)
            db.session.commit()
        else:
            for (rd_id, seq), count in self.collection.items():
                if count > self.commit_threshold:  # only over 2 count sequence will be committed.
                    # self.collection.pop(k)
                    self.length_count[len(seq)] += count
                    # self.commit_result[k] += count
                    self.set_commit_result(rd_id,count)

    def finnal_commit(self):
        rds = [Rounds.query.get(k) for k, *_ in self.sampleinfo]
        for r in rds:
            r.totalread = sum([i.count for i in r.sequences ])
        db.session.commit()

    def process(self, commit):
        counter = 0
        # print('*** total read:', self._totalread)
        for fw_fs_rev_rs in self.file_generator():
            counter += 1
            _set_task_progress(counter/(self.total)*100,start=0,end=95)
            self.process_seq(fw_fs_rev_rs)
            # if counter % 52345 == 0:
            #     self.commit(commit)
        # print('*** ending total read:', counter)
        self.commit(commit)
        self.finnal_commit()
        return self.results(commit), self.commit_result_dict()

    def set_commit_result(self, round_id, count):
        self.unique_commit[round_id]+=1
        self.total_commit[round_id]+=count

    def commit_result_dict(self):
        return {i: f"{self.unique_commit[i]}/{self.total_commit[i]}" for i in self.unique_commit.keys()}

    def write_failures(self):
        tosave = current_app.config['UPLOAD_FOLDER'] + '/processing_failuresequences.txt'
        # fail = list(self.failure_collection.items())
        with open(tosave,'a') as f:
            f.write("="*100+'\n'+"="*100+'\n')
            f.write(f'Processing files: \nFile1:{self.f1}\nFile2:{self.f2}\nDate:{datetime.now().strftime("%Y/%m/%d %H:%M")}\n')
            f.write("="*40+'Top 50 failure sequences'+"="*40+"\n")
            for i,j in self.failure_collection.most_common(50):
                f.write("{:<9}{}\n".format(j,i))
            f.write("="*40+'Top 50 Partial failure sequences'+"="*40+"\n")
            for i, j in self.partial_failure_collection.most_common(50):
                f.write("{:<9}{}\n".format(j, i))
               
            f.write('Top 50 abberant Primer - NGS primer combinations\n')
            f.write("\n".join(["<{}> - {}".format(" ".join(f"{k[0]}:{k[1]}" for k in i), j)
                               for i, j in self.primer_collection.most_common(50)]))
            f.write('\n')

    def results(self,commit):
        ttl = self.total
        total_pass_filter = sum(self.collection.values())
        _total_commit = sum(self.total_commit.values())
        smry = "Total reads: {} / 100%\nPass primers match: {} / {:.2%}\nPass F-R equal length filter: {} / {:.2%}\nPass Q-score filter (Q>{}): {} / {:.2%}\nPass reverse-complement filter: {} / {:.2%}\n".format(
            ttl, self.success, self.success/ttl, self.length_filter, self.length_filter/ttl, self.score_threshold ,self.score_filter, self.score_filter/ttl, self.revcomp, self.revcomp/ttl, )
        smry = smry+ "Filters used: {}\n".format(self.filter_display())

        temp_counter = Counter()
        bins = [1,2,4,8,12,20]
        for val in self.collection.values():
            for b in bins:
                if val<b+1:
                    temp_counter[b]+=val
        smry+="Post non-Count filters Count break points: \n"+"; ".join("{:.2%}<{}".format(temp_counter[k]/ttl,k+1) for k in bins) + "\n"
        # smry = smry + f"Count threshold used: {self.commit_threshold}\n"
        leftover = total_pass_filter - _total_commit
        smry = smry + "Total commit after all filters: {} / {:.2%}\nUncommited (total count < {}): {} / {:.2%}\n".format(
            _total_commit, _total_commit/ttl, self.commit_threshold+1, leftover, leftover/ttl)
        length = self.length_count.most_common(4)
        length = '; '.join(["{:.1%} {}nt".format(j/_total_commit,i) for i, j in length])
        smry = smry + "Length Distribution: {}\n".format(length)
        # primers = sorted([i for i in self.primer_collection.items()],key=lambda x: x[1],reverse=True)
        # sumprimers = sum([i[1] for i in primers])
        # index = sorted([i for i in self.index_collection.items()],key=lambda x: x[1],reverse=True)
        # sumindex = sum([i[1] for i in index])
        smry = smry + "Aberrant selection primers found in {} / {:.2%} reads\n".format(self.aberrant_primers, self.aberrant_primers/ttl)
        smry += "Most common selection - NGS combinations are:\n"
        # primers[0:5]:
        smry += "\n".join(["<{}> - {}".format(" ".join(f"{k[0]}:{k[1]}" for k in i), j)
                           for i, j in self.primer_collection.most_common(8)])
        # smry +="\nAbberant NGS sequencing primers found in {} / {:.2%} reads\n".format(sumindex,sumindex/ttl)
        # smry +="Most common ones are: "
        # for i, j in index[0:5]:
            # smry += "<{}>-{} ".format(i, j)
        smry+="\nNo match failures: {} / {:.2%}".format(self.failure,self.failure/ttl)

        return smry

def parse_ngs_data(nsg_id, commit, filters):
    f1,f2,sampleinfo=generate_sample_info(nsg_id)

    NSProcessor = NGS_Sample_Process(f1, f2, sampleinfo, filters)
    result, commit_result = NSProcessor.process(commit)
    NSProcessor.write_failures()
    # processing file1 and file2 and add to database
    nsg = NGSSampleGroup.query.get(nsg_id)
    if commit=='retract':
        nsg.processingresult=""
        # nsg.commit_threshold = 0
        # nsg.score_threshold = 0
        nsg.filters = []
        nsg.commit_result = {}
    elif commit == 'false':
        nsg.temp_result = result
        nsg.temp_commit_result = commit_result
    else:
        nsg.processingresult=result
        # nsg.commit_threshold = commit_threshold
        nsg.filters = filters
        nsg.commit_result = commit_result
        # nsg.score_threshold = score_threshold
    nsg.save_data()
    nsg.task_id = None
    db.session.commit()
    _set_task_progress(100)

def test_worker(n):
    for i in range(n):
        print("****runging test -", i)

def load_rounds(id):
    analysis = Analysis.query.get(id)
    analysis_id = str(analysis.id)
    filepath = os.path.join(
        current_app.config['ANALYSIS_FOLDER'], analysis_id)
    create_folder_if_not_exist(filepath)
    dr=DataReader(name=analysis.name,filepath=filepath)
    dr.load_from_ngs_server(analysis.rounds,callback=_set_task_progress)
    analysis.analysis_file = os.path.join(analysis_id, dr.save_pickle())
    analysis.pickle_file = os.path.join(analysis_id, dr.save_pickle('_advanced'))
    ch=dr.sequence_count_hist(save=True)
    lh=dr.sequence_length_hist(save=True)
    analysis.hist = [os.path.join(
        analysis_id, ch), os.path.join(analysis_id, lh)]
    analysis.task_id=''
    analysis.cluster_para=''
    analysis.heatmap=''
    analysis.cluster_table=''
    analysis.save_data()
    db.session.commit()
    _set_task_progress(100)

def build_cluster(id):
    analysis = Analysis.query.get(id)
    analysis_id = str(analysis.id)
    dr = analysis.get_datareader
    d,lb,ub,ct=analysis.cluster_para
    dr.df_cluster(d,(lb,ub),ct,clusterlimit=1000,findoptimal=True,callback=_set_task_progress)
    dr.in_cluster_align(callback=_set_task_progress)
    dr.df_trim()
    dr.alias={}
    dr.rename_from_known_sequence()
    analysis.analysis_file = os.path.join(analysis_id, dr.save_pickle())
    hname,df=dr._plot_heatmap(returndf=True)
    analysis.heatmap = hname[0]
    roundnamedict = dict(zip(df.columns.tolist(),analysis._rounds))
    maxrounddict = {k:roundnamedict[i] for k,i in df.idxmax(axis=1).to_dict().items()}
    topcluster = df.index.tolist()
    result = []
    ks = KnownSequence.query.all()
    similaritythreshold=10
    for i in topcluster:
        a = i+bool(dr.alias.get(i, 0))*f" / {dr.alias.get(i,0)}"

        repseq = dr[i].rep_seq().replace('-', '')
        seq = Sequence.query.filter_by(aptamer_seq=repseq).first()
        maxround=maxrounddict[i]

        ksdistance = [lev_distance(
            repseq, i.rep_seq, ) for i in ks]  # similaritythreshold+abs(i.length-len(repseq))
        similarity = sorted([(i, j) for i, j in zip(
            ks, ksdistance)], key=lambda x: x[1])
        similarity = [(ks, i) for ks, i in similarity if i <= (
            similaritythreshold+abs(ks.length-len(repseq)))][0:5]
        similarity = [ ( f"{ks.sequence_name} [{i}]", ks.id) for ks,i in similarity ]
        result.append((a, i, seq and seq.id_display, seq and seq.id, maxround, similarity))

    analysis.cluster_table=result

    analysis.task_id = ''
    analysis.save_data()
    db.session.commit()
    _set_task_progress(100)

def dynamic_lev_distance(seq,fix_seq="",diff_ratio=0.4):
    query_length = len(fix_seq)
    cutoff = abs(len(seq)-query_length)+query_length*diff_ratio
    dis = lev_distance(seq, fix_seq)  # cutoff
    if dis<cutoff:
        return dis
    return None

def lev_distance_search(query,table):
    #table can be sequence, primer, known_sequence
    query=query.strip()
    target = models_table_name_dictionary.get(table)
    seq_atr_name = dict(primer='sequence', known_sequence='rep_seq',
                   sequence='aptamer_seq').get(table)
    result = []
    total = target.query.count()
    have_more=True
    page = 0
    pagelimit = 10000
    task = partial(dynamic_lev_distance,fix_seq=query,diff_ratio=0.3)
    while have_more:
        page+=1
        searchcontent = db.session.query(
            getattr(target, 'id'), getattr(target, seq_atr_name)).paginate(page,pagelimit,False)
        if not searchcontent.has_next:
            have_more = False
        searchcontent = searchcontent.items
        tempresult = poolwrapper(task,[i[1] for i in searchcontent],callback=_set_task_progress,
                                 progress_gap=((page-1)*pagelimit / total * 99, min(99, page*pagelimit / total * 99)))

        for _dis, (_id, _s) in zip(tempresult, searchcontent):
            if _dis != None:
                result.append((_id, _dis))
    result.sort(key=lambda x:x[1])
    result = result[0:50]
    _set_task_progress(100)
    return dict(result=result,query=query)

def advanced_task(id,funcname,para):
    progress_callback = _set_task_progress
    analysis = Analysis.query.get(id)
    try:
        para = eval(f"dict({para})")
        dr = analysis.get_advanced_datareader()
        progress_callback(5)
        func=getattr(dr, funcname)
        _return = signature(func).return_annotation.split(',')
        result = func(**para) 
        if len(_return)==1:
            result = [result]
        output = dict(zip(_return,result))
        analysis.advanced_result[funcname]['output'].update(output) 
        analysis.advanced_result[funcname]['output']['task'] = None 
        analysis.save_data()
        db.session.commit()
    except Exception as e:
        analysis.advanced_result[funcname]['output']['text']=[f"Error: {e}"]
        analysis.advanced_result[funcname]['output']['task'] = None
        analysis.save_data()
        db.session.commit()

    progress_callback(100)
        

if __name__ == '__main__':
    """test data processing module"""
