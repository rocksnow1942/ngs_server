import shelve


key='ams113'
data={}

with shelve.open('cache/plojo_data',writeback=True) as hd:
    # data_index = hd['index']
    for i in range(1,7):
        hd['ams122'+str(i)]=data['ams122'+str(i)]

        