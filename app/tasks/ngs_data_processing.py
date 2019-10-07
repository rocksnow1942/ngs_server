from rq import get_current_job
from app import db
from app.models import NGSSampleGroup,Primers,Rounds,Sequence,KnownSequence,Task,SeqRound,Analysis
from app import create_app
import os
from flask import current_app
import json
from itertools import islice
from app.utils.ngs_util import reverse_comp, file_blocks, create_folder_if_not_exist,lev_distance
from collections import Counter
import re
from app.utils.analysis import DataReader



app = create_app(keeplog=False)
app.app_context().push()

def _set_task_progress(progress):
    job = get_current_job()
    if job:
        task = Task.query.get(job.get_id())
        task.progress = round(progress,2)
        if progress >= 100:
            task.complete = True
        db.session.commit()

class NGS_Sample_Process:
    """
    process files into database commits. assuming files are already validated.
    """

    def __init__(self,f1,f2,sampleinfo):
        self.f1 = f1
        self.f2 = f2
        self.sampleinfo = sampleinfo
        self.collection = Counter()
        self.primer_collection=Counter() # log wrong primers
        self.index_collection=Counter() # log wrong index
        self.length_count=Counter()
        self.failure = 0 # log other un explained.
        self.total = 0 # total reads
        self.revcomp = 0 # passed rev comp reads
        self.success = 0 # find match
        self.pattern = [(re.compile(j+'[AGTCN]{0,3}'+l) , re.compile(m+'[AGTCN]{0,3}'+k) ) for i,j,k,l,m in self.sampleinfo]
        self._totalread = self.totalread()
        ngsprimer = [(i.name, i.sequence)
                     for i in Primers.query.filter_by(role='NGS').all()]
        ngsprimer = ngsprimer + [(i,reverse_comp(j)) for i,j in ngsprimer]
        samplengsprimer = {i[j] for i in self.sampleinfo for j in [1,2]}
        self.ngsprimer = [i for i in ngsprimer if i[1] not in samplengsprimer]
        selectionprimer = [(i.name, i.sequence) for i in Primers.query.filter(
                    Primers.role.in_(('PD', 'SELEX'))).all()]
        selectionprimer = selectionprimer + [(i,reverse_comp(j)) for i,j in selectionprimer]
        ssp = {i[j] for i in self.sampleinfo for j in [3,4] }
        self.selectionprimer = [i for i in selectionprimer if i[1] not in ssp]
        self.ks = {i.rep_seq:i.id for i in KnownSequence.query.all()}

    def file_generator(self):
        with open(self.f1,'rt') as f, open(self.f2,'rt') as r:
            for line,rev in zip(islice(f,1,None,4),islice(r,1,None,4)):
                line=line.strip()
                rev=rev.strip()
                self.total+=1
                if line == reverse_comp(rev):
                    self.revcomp+=1
                    yield line

    def process_seq(self,seq):
        nomatch = True
        for (rdid,*(primers)),patterns in zip(self.sampleinfo,self.pattern):
            matched = self.match_pattern(seq,primers,patterns)
            if matched:
                nomatch = False
                self.success +=1
                self.collection[(rdid,matched)]+=1
        if nomatch: self.log_unmatch(seq)

    def match_pattern(self,seq,primers,patterns):
        match = False
        if all([i in seq for i in primers]):
            ffind = patterns[0].search(seq)
            if ffind:
                findex = ffind.span()[1]
                rfind = list(patterns[1].finditer(seq))
                if rfind:
                    rindex = rfind[-1].span()[0]
                    match = seq[findex:rindex]
        return match

    def log_unmatch(self,seq):
        ab = True
        for n,p in self.selectionprimer:
            if p in seq:
                ab = False
                self.primer_collection[n]+=1
                idx = seq.index(p)
                for n2, p2 in self.ngsprimer:
                    if p2 in seq[idx-3-len(p2): idx] or p2 in seq[idx+len(p):idx+len(p)+3 + len(p2)]:
                        self.index_collection[n2]+=1
        if ab: self.failure+=1

    def totalread(self):
        with open(self.f1, 'rt') as f:
            fb1 = file_blocks(f)
            totalread = sum(bl.count("\n") for bl in fb1)
        return totalread/4

    def commit(self):
        for k in list(self.collection.keys()):
            rd_id,seq = k
            count = self.collection[k]
            if count > 1:
                self.collection.pop(k)
                self.length_count[len(seq)]+=count
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

    def finnal_commit(self):
        rds = [Rounds.query.get(k) for k, *_ in self.sampleinfo]
        for r in rds:
            r.totalread = sum([i.count for i in r.sequences ])
        db.session.commit()

    def process(self):
        counter = 0
        print('*** total read:', self._totalread)
        for seq in self.file_generator():
            counter += 1
            _set_task_progress(counter/(self._totalread+10)*100)
            self.process_seq(seq)
            if counter % 52345 == 0:
                self.commit()
        print('*** ending total read:', counter)
        self.commit()
        self.finnal_commit()
        return self.results()

    def results(self):
        ttl = self.total
        smry = "Total reads: {} / 100%\nPass reverse-complimentary: {} / {:.2%}\nPass primers match: {} / {:.2%}\n".format(
            ttl, self.revcomp,self.revcomp/ttl, self.success,self.success/ttl)
        leftover = len(self.collection)
        smry = smry + "Total commited: {} / {:.2%}\nUncommited (total count=1): {} / {:.2%}\n".format(
            self.success-leftover, (self.success-leftover)/ttl, leftover,leftover/ttl)
        length = self.length_count.most_common(4)
        total = sum([i for i in self.length_count.values()])
        length = '; '.join(["{:.1%} {}nt".format(j/total,i) for i, j in length])
        smry = smry + "Length Distribution: {}\n".format(length)
        primers = sorted([i for i in self.primer_collection.items()],key=lambda x: x[1],reverse=True)
        sumprimers = sum([i[1] for i in primers])
        index = sorted([i for i in self.index_collection.items()],key=lambda x: x[1],reverse=True)
        sumindex = sum([i[1] for i in index])
        smry = smry + "Aberrant selection primers found in {} / {:.2%} reads\n".format(sumprimers,sumprimers/ttl)
        smry += "Most common ones are: "
        for i,j in primers[0:5]:
            smry += "{}-{} ".format(i,j)
        smry +="\nAbberant NGS sequencing primers found in {} / {:.2%} reads\n".format(sumindex,sumindex/ttl)
        smry +="Most common ones are: "
        for i, j in index[0:5]:
            smry += "{}-{} ".format(i, j)
        smry+="\nFailures: {} / {:.2%}".format(self.failure,self.failure/ttl)
        return smry

class NGS_Sample_Process_Tester(NGS_Sample_Process):
    #TODO: run test on ngs data processing
    def __init__(self, f1, f2, sampleinfo,save_loc):
        self.save_loc=save_loc
        self.f1 = f1
        self.f2 = f2
        self.sampleinfo = sampleinfo
        self.collection = Counter()
        self.primer_collection = Counter()  # log wrong primers
        self.index_collection = Counter()  # log wrong index
        self.failure = 0  # log other un explained.
        self.total = 0  # total reads
        self.revcomp = 0  # passed rev comp reads
        self.success = 0  # find match
        self.pattern = [(re.compile(j+'[AGTCN]{0,3}'+l), re.compile(
            m+'[AGTCN]{0,3}'+k)) for i, j, k, l, m in self.sampleinfo]
        self._totalread = self.totalread()
        ngsprimer = [("i701",	"CGAGTAAT"),
                     ("i702",	"TCTCCGGA"),
                     ("i703",	"AATGAGCG"),
                     ("i704",	"GGAATCTC"),
                     ("i705",	"TTCTGAAT"),
                     ("i706",	"ACGAATTC"),
                     ("i707",	"AGCTTCAG"),
                     ("i708",	"GCGCATTA"),
                     ("i709",	"CATAGCCG"),
                     ("i710",	"TTCGCGGA"),
                     ("i711",	"GCGCGAGA"),
                     ("i712",	"CTATCGCT")]
        ngsprimer = ngsprimer + [(i, reverse_comp(j)) for i, j in ngsprimer]
        samplengsprimer = {i[j] for i in self.sampleinfo for j in [1, 2]}
        self.ngsprimer = [i for i in ngsprimer if i[1] not in samplengsprimer]
        selectionprimer = [('SOMAFP', 'CGCCCTCGTCCCATCTC'),
                           ('SOMARP', 'CGTTCTCGGTTGGTGTTC'),
                           ('PatsFP', 'ACATGGAACAGTCGAGAATCT'),
                           ('PatsRP', 'ATGAGTCTGTTGTTGCTCA'),
                           ('N2FP', 'TCTGACTAGCGCTCTTCA'),
                           ('LadderRP', 'CGACTCGACTAAACAGCAC'),
                           ('LadderRPC', 'GTGCTGTTTAGTCGAGTCG'),
                           ('IronmanTFP', 'GATGTGAGTGTGTGACGATG'),
                           ('IronmanRP', 'GGTCTTGTTTCTTCTCTGTG'),
                           ('IronmanRPC', 'CACAGAGAAGAAACAAGACC'),
                           ('VEGF33RP1C', 'GAGATCCGACTCACTGG')]
        selectionprimer = selectionprimer + \
            [(i, reverse_comp(j)) for i, j in selectionprimer]
        ssp = {i[j] for i in self.sampleinfo for j in [3, 4]}
        self.selectionprimer = [i for i in selectionprimer if i[1] not in ssp]

    def commit(self,counter):
        towrite=[]
        for k in list(self.collection.keys()):
            rd_id, seq = k
            count = self.collection[k]
            if count > 1:
                towrite.append(self.collection.pop(k))
        with open(self.save_loc, 'a') as f:
            f.write()

    def process(self):
        import pickle
        for seq in self.file_generator():
            self.process_seq(seq)
        with open(self.save_loc, 'wb') as f:
            self.collection['result'] = self.results()
            pickle.dump(self.collection,f)
        return self.collection

def generate_sample_info(nsg_id):
    """
    sample info is a list consist of [ () ()]
    (round_id, fpindex, rpcindex, fp, rpc)
    """
    nsg = NGSSampleGroup.query.get(nsg_id)
    savefolder = current_app.config['UPLOAD_FOLDER']
    f1 = os.path.join(savefolder, json.loads(nsg.datafile)['file1'])
    f2 = os.path.join(savefolder, json.loads(nsg.datafile)['file2'])
    sampleinfo = []
    for sample in nsg.samples:
        round_id = sample.round_id
        fpindex = Primers.query.get(sample.fp_id or 1).sequence
        rpindex = Primers.query.get(sample.rp_id or 1).sequence
        rd = Rounds.query.get(round_id)
        fp = Primers.query.get(rd.forward_primer or 1).sequence
        rp = Primers.query.get(rd.reverse_primer or 1).sequence
        sampleinfo.append((round_id,fpindex,reverse_comp(rpindex),fp,reverse_comp(rp)))
    return f1,f2,sampleinfo

def parse_ngs_data(nsg_id):
    f1,f2,sampleinfo=generate_sample_info(nsg_id)
    NSProcessor = NGS_Sample_Process(f1,f2,sampleinfo)
    result = NSProcessor.process()
    # processing file1 and file2 and add to database
    nsg = NGSSampleGroup.query.get(nsg_id)
    nsg.processingresult=result
    nsg.task_id = None
    db.session.commit()
    _set_task_progress(100)


def test_worker(n):
    for i in range(n):
        print("****runging test -", i)


def load_rounds(id):
    analysis = Analysis.query.get(id)
    filepath = os.path.join(
        current_app.config['ANALYSIS_FOLDER'], str(analysis.id))
    create_folder_if_not_exist(filepath)
    dr=DataReader(name=analysis.name,filepath=filepath)
    dr.load_from_ngs_server(analysis.rounds,callback=_set_task_progress)
    dr.save_json()
    ch=dr.sequence_count_hist(save=True)
    lh=dr.sequence_length_hist(save=True)
    analysis.analysis_file=os.path.join(filepath,analysis.name+'.json')
    analysis.hist = [os.path.join(
        str(analysis.id), ch), os.path.join(str(analysis.id), lh)]
    analysis.task_id=''
    analysis.cluster_para=''
    analysis.heatmap=''
    analysis.cluster_table=''
    analysis.save_data()
    db.session.commit()
    _set_task_progress(100)

def build_cluster(id):
    analysis = Analysis.query.get(id)
    dr = analysis.get_datareader
    d,lb,ub,ct=analysis.cluster_para
    dr.df_cluster(d,(lb,ub),ct,clusterlimit=1000,findoptimal=True,callback=_set_task_progress)
    dr.in_cluster_align(callback=_set_task_progress)
    dr.df_trim(save_df=True)
    dr.rename_from_ks_server(ks=KnownSequence.query.all())
    dr.save_json()
    hname,df=dr.plot_heatmap(save=True)
    analysis.heatmap = os.path.join(str(analysis.id), hname)
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
            repseq, i.rep_seq, similaritythreshold+abs(i.length-len(repseq))) for i in ks]
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


if __name__ == '__main__':
    """test data processing module"""

    file1 = "/Users/hui/Desktop/exp46_30-217785519/20190412_S1_R1_001.fastq"
    file2 = "/Users/hui/Desktop/exp46_30-217785519/20190412_S1_R2_001.fastq"


    forward ,reverse = [],[]
    with open(file1, "r") as f, open(file2,'rt') as r:
        for line in islice(f,1,None,4):
            forward.append(line.strip())
        for line in islice(r,1,None,4):
            reverse.append(line.strip())

    len(forward)
    len(reverse)
    forward[0]
    reverse[0]
    count=0
    for i,j in zip(forward,reverse):
         if i!=reverse_comp(j):
                count+=1

    print(count)
    all([i in 'abc' for i in 'abcd'])
