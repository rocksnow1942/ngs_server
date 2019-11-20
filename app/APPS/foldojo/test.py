from _structurepredict import Structure as S
from _structurepredict import dotbracket_to_tuple
from _structurepredict import DotGraph
import ViennaRNA as RNA

from NUPACK import *

defect(['ATCG'],'....')

import RNA
s=S('ATCATC')
RNA.get_xy_coordinates(s1)
s.fold(method='ViennaRNA')

fc=RNA.fold_compound('ACGAGAG')

s1='.....((((.....)))).....((...{{{..))..}}}.{{{....}}}.'
s2='.....((((.....)))).....((...{{{..))..}}}.{{{....}}}.'
sq='ATATAATTTTTAAGCGC'
s0='.((...{{{..))..}}}.(((....))).'
s0='(((((..&.....)))))'
 RNA.bp_distance(s1,s2)
pt=dotbracket_to_tuple(s0)
pt
dg=DotGraph(sq, s0, -1,[0.1]*len(s0),pt)

dg.plot_2d()



from NUPACK import *
import numpy as np
rna_seq = ['GGGCUGUUUUUCUCGCUGACUUUCAGCCCCAAACAAAAAAUGUCAGCA'];
dna_seqs = ['AGTCTAGGATTCGGCGTGGGTTAA',
            'TTAACCCACGCCGAATCCTAGACTCAAAGTAGTCTAGGATTCGGCGTG',
            'AGTCTAGGATTCGGCGTGGGTTAACACGCCGAATCCTAGACTACTTTG']
dna_struct = '((((((((((((((((((((((((+))))))))))))))))))))))))((((((((((((.(((((((((((+........................))))))))))).))))))))))))'

pfunc(v, material = 'rna')


energy(dna_seqs, dna_struct, material = 'dna')


pfunc(v, material = 'rna', multi = True, pseudo = False)

v=['ACCCTTGCTTGCGTAGCATTTTACCAGTGAGTCGGATCTCCGCATATCTGCG','ACCCTTGCTTGCGTAGCATTTTACCAGTGAGTCGGATCTCCGCATATCTGCG']
mfe(v, material = 'rna')
v=['ACCCTTGCTTGCGTAGCATTTTACCAGTGAGTCGGATCTCCGCATATCTGCG']
mfe(v, material = 'rna')
[('...((.((((((..............)))))).)).....((((....))))', '-9.500')]
v=['ACCCTTGCTTGCGTAGCATTTTACCAGTGAGTCGGATCTCCGCATATCTGCG']

defect(v,'...((.((((((..............)))))).)).....((((....))))')

res=pairs(v,cutoff=0.0)
pairdict={(i[0],i[1]):i[2] for i in res}
pairdict

t=37+273.15
kT=8.314*t/4.184e3 # Boltzmann constant * Gas constant then convert kJ to J.
kT=np.exp(-1/kT)
Q=kT**-11.2695885
kT**-9.5/Q

a=Align

prob(v,'...((.((((((..............)))))).)).....((((....))))')
defect(v,'...((.((((((..............)))))).)).....((((....))))')


pseu=['UCGACUGUAAAAAAGCGGGCGACUUUCAGUCGCUCUUUUUGUCGCGCGC']

r=subopt(v,1,material='rna',dangles='some',sodium=0.1,multi=False,pseudo=False)
r

len(r)

arg,input=setup_nupack_input(exec_name = 'subopt', sequences = v, ordering = None,
                   material = 'rna', sodium = 1.0, magnesium = 0.0,
                   dangles = 'some', T =37, multi = True, pseudo = False)

input += '\n' + str(2)

out=call_with_file(arg,input,'.subopt')


  ## Parse and return output
structs = []
for i, l in enumerate(out):
    if l[0] == '.' or l[0] == '(':
      s = l.strip()
      e = out[i-1].strip()
      structs.append((s,e))

len(structs)





print(input)
