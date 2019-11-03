import shelve


key = 'ams144'

with shelve.open('cache/hplc_data', writeback=False) as hd:
    data_index = hd['index']
    meta = hd[key].copy()
    raw = hd[key+'raw'].copy()


meta
len(str(data_index))
data_index



print(*meta.keys(), sep='\n')

print(*raw.keys(), sep='\n')




import time
def timer():
    t = time.time()
    def wrapped(info=""):
        print('***Time Elapsed: {:.2f}s. - {}'.format(time.time()-t,info))
    return wrapped
