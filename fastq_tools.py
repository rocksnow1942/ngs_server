# break fastq files into smaller files
def break_fastq_file(file, lines, tosave):
    with open(file, 'rt') as f, open(tosave, 'wt') as t:
        for i in range(lines*4):
            t.write(f.readline())


file1 = '/home/hui/ngs_server/app/cache/ngs_data_upload/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R1.fastq'
file2 = '/home/hui/ngs_server/app/cache/ngs_data_upload/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R2.fastq'

tosave1 = '/home/hui/ngs_server/app/cache/ngs_data_upload/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R1s.fastq'
tosave2 = '/home/hui/ngs_server/app/cache/ngs_data_upload/2019-11-07 (Exp63) SELEX pools for SIS6 WiCiK_R2s.fastq'
break_fastq_file(file1, 100, tosave1)
break_fastq_file(file2, 100, tosave2)




