from analysis import DataReader
import pandas as pd
import json
import numpy as np

df = pd.read_csv('/Users/hui/Documents/Scripts/ngs_server/app/utils/test.csv',index_col=0)
dr = DataReader('test',temp=1)

dr=DataReader.load('/Users/hui/Documents/Scripts/ngs_server/app/utils/raw_data/test.datareader')

dr = DataReader.load('/Users/hui/Documents/ngs_data/VEGF/20190828_exp58_exp59/raw_data/20190828_exp58_exp59.datareader')

for k,i in dr.__dict__.items():
    print(k, '=>')
ad=dr.__dict__['align']['C1'].to_dict()
type(ad)
for k,i in ad.items():
    print(k,type(i))

for k,i in dr.__dict__['align']['C1'].to_dict().items():
    try:
        json.dumps(i)
    except:
        print(k,i)

a=    np.array([[2, -1, -1, -1, -1.1],
                                           [-1, 2, -1, -1, -1.1],
                                           [-1, -1, 2, -0.6, -1.1],
                                           [-1, -1, -0.6, 2, -1.1],
                                           [-1.1,  -1.1, -1.1, -1.1, 1]])


json.dumps(list(a))

for k,i in dr.align['C1'].__dict__.items():
    print(k, '=>' ,)

j = dr.jsonify()

dr.save_json('newtest.json')
with open('newtest.json') as f:
    data=json.load(f)

type(data)

new=DataReader.load_json('newtest.json')


dr.name
dr.working_dir
dr.alias
dr.df
dr.processing_para
dr._df
dr.save_loc



dr.df=df
dr.df
dr._df.info()
dr.df.info()

d = df.to_dict()

df = pd.DataFrame(d)

dr.df.head()
df.head()
with open()

len(dr.df)

dr.df_cluster()

dr.in_cluster_align()

dr.plot_logo('C1')
dr.df_trim()
print(dr.align['C1'].format())
dr.plot_cluster_trend('C2')
dr.plot_pie()

dr.plot_heatmap()
dr.save_loc='/Users/hui/Documents/Scripts/ngs_server/app/utils'

dr.save()
