import shelve


key='ams113'
data={}

with shelve.open('cache/plojo_data',writeback=True) as hd:
    data_index = hd['index']
    keys = list(hd.keys())
    for k,i in hd.items():
        data[k]=i
    # for i in range(1,7):
    #     hd['ams12'+str(i)]=data['ams12'+str(i)]


'index': set()

len(str(data_index))
data_index.keys()
type(data_index['0-temporary'])


data.keys()

data['index']

str(data['ams1114'])

import json

a=  json.dumps([1,2,3,4])
a
json.dumps(data['ams999'])


a=set('abc')
a

b=set('bcd')

a & b
