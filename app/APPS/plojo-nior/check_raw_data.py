import shelve


key = 'ams144'

with shelve.open('cache/hplc_data', writeback=False) as hd:
    data_index = hd['index']
    meta = hd[key].copy()
    raw = hd[key+'raw'].copy()


meta
data_index

print(*meta.keys(), sep='\n')

print(*raw.keys(), sep='\n')
