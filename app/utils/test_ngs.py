from analysis import DataReader
import pandas as pd
import json
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv('/Users/hui/Documents/Scripts/ngs_server/app/utils/test.csv',index_col=0)
dr = DataReader('test',temp=1)

dr=DataReader.load('/Users/hui/Documents/Scripts/ngs_server/app/utils/raw_data/test.datareader')

dr = DataReader.load('/Users/hui/Documents/ngs_data/VEGF/20190828_exp58_exp59/raw_data/20190828_exp58_exp59.datareader')

dr=DataReader.load_json('/Users/hui/Documents/Scripts/ngs_server/app/cache/analysis_data/5/all analysis.json')
dr=DataReader.load_json('/Users/hui/Documents/Scripts/ngs_server/app/cache/analysis_data/3/more rounds.json')
df=dr.df.sort_values(by=['sum_per','sum_count'],ascending=[False,False])
dr.list_all_rounds()
d=dr.df_info(show=False)
d.to_dict()
dr.df_table()
dr.info()
dr.plot_logo('C1')
sum(dr['C1'].count)
len(dr['C1'].count)
print()
int(float('124.0'))
dr['C1'].align_score()
[i.split('\t') for i in dr['C1'].format(count=1,order=1,returnraw=1)]
dr.df.head()
dr.sequence_length_hist()
dr.processing_para
dr.df.loc['C539']
dr.plot_heatmap(top=50)
dr.cluster
res= dr.slice_df(round='all')
nd_per,nd_count = res[0].sum(axis=1),res[1].sum(axis=1)
nd_count

dr.df
dr.cluster
dr.df=
dr._scope_('cluster')

dr.slice_df(round)
dr._scope_('cluster')
dr.sort_align()

dr['C539']


dr['C1'].dna_logo()
dr.find('C1')
plt.figure()

df.loc['C1',:].max()
df.columns.tolist().index('pbspk_4')
df.idxmax(axis=1).to_dict()
f,df=dr.plot_heatmap(save=True)
plt.show(f)
import io
f.savefig(io.BytesIO(),format='svg')
dr.df['sum_count'].sum()
dr.translate('C2')
dr.sequence_count_hist()
bool(dr.alias.get('C1',0))*f" / {dr.alias.get('C1',0)}"
df=dr.plot_pie(50,plot=False,translate=False).drop(labels='Others',axis=0).index.tolist()

dr['C1'].rep_seq()



df
re


dr['C1']


dr.sequence_length_hist(save=False)
dr.df.head()

ld = dr.df['sum_count']
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

ld2 = [i for i in ld for j in range(int(i))]
len(ld2)


bin=np.geomspace(1,3500,1000)

ax=ld.hist(density=1,histtype='step',cumulative=1,bins=bin)
ax.set_xscale('log')
# ax.set_xticks([1,2,3,4,5,10,20,30,40,100,200,1000])
ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
ax.set_title('test')



bin=np.geomspace(1,int(max(ld2)*1.2),int(max(ld2)*1.2))
fig,ax=plt.subplots()
ax.hist(ld2,density=1,histtype='step',cumulative=1,bins=bin)
# ax=ld2.hist(density=1,histtype='step',cumulative=1,bins=bin)
ax.set_xscale('log')
# ax.set_xticks([1,2,3,4,5,10,20,30,40,100,200,1000])
ax.set_title('test')
ax.grid(1)


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
