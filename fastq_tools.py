# break fastq files into smaller files
def break_fastq_file(file, lines, tosave):
    """
    take first few lines from a fastq file and save to tosave.
    """
    with open(file, 'rt') as f, open(tosave, 'wt') as t:
        for i in range(lines*4):
            t.write(f.readline())

from itertools import islice
def fastq_reader(*files,readgap=4):
    """
    return every <readgap> line of a list of fastq files
    """
    files = [open(i) for i in files]
    fr = [islice(i,1,None,readgap) for i in files]
    for seqs in zip(*fr):
        yield (i.strip() for i in seqs)
    for i in files: i.close()


file1 = '/home/hui/ngs_server/app/cache/ngs_data_upload/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R1.fastq'
file2 = '/home/hui/ngs_server/app/cache/ngs_data_upload/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R2.fastq'

tosave1 = '/home/hui/ngs_server/app/cache/ngs_data_upload/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R1s.fastq'
tosave2 = '/home/hui/ngs_server/app/cache/ngs_data_upload/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R2s.fastq'
break_fastq_file(file1, 100, tosave1)
break_fastq_file(file2, 100, tosave2)
