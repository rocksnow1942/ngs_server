from os import path
import platform


localmode=False


systemname = platform.node()
if localmode:
    _file_path = path.dirname(__file__)+ '/cache'
    file_path = _file_path
    upload_data_folder = _file_path
    temp_position = _file_path

elif systemname.startswith('huis-mac-mini'):
    _file_path = path.dirname(__file__)
    file_path = '/Users/hui/Cloudstation/R&D Backup/Plojo backup'# file path on my mac
    upload_data_folder = _file_path
    temp_position = _file_path

elif systemname.startswith('Huis-MacBook'):
    _file_path = path.dirname(__file__)
    file_path = '/Users/hui/Aptitude_Cloud/Aptitude Users/R&D Backup/Plojo backup'
    upload_data_folder = _file_path
    temp_position = _file_path

elif systemname == 'plojo':
    file_path = '/home/hui/AptitudeUsers/R&D Backup/Plojo backup'
    temp_position= '/home/hui/AptitudeUsers/R&D Backup/Plojo backup/hplc_temp'
    upload_data_folder = '/home/hui/AptitudeUsers/R&D/Shared Data/Plojo/!HPLC_UPLOAD'
else:
    file_path = "C:\\Users\\aptitude\\Aptitude-Cloud\\R&D Backup\\Plojo backup"
    upload_data_folder = "C:\\Users\\aptitude\\Aptitude-Cloud\\R&D\\Shared Data\\Plojo\\!HPLC_UPLOAD"
    temp_position = "C:\\Users\\aptitude\\Aptitude-Cloud\\R&D Backup\\Plojo backup\\hplc_temp"
file_name = 'hplc_data'





# # define raw data class and load rawdata.
# class Data():
#     """
#     class to interact with shelve data storage.
#     data stored in shelvs as follows:
#     index : a dict contain experiment information; { ams5:{'name': 'experiment name','date': "20190101",'author':'jones'}, ams23:{}}
#     meta information and raw data of each experiment is under: "amsXX" and "amsXXraw"
#     meta information example:
#             'ams39':{
#             "ams39-run0": {
#                 "speed": 1.0,
#                 "date": "20190409",
#                 "name": "PHENORP YPEGBS3 2-5V1RXN 0-5MMBS3 35C 1UG 5-60 28M 1MM",
#                 "A": {
#                     "y_label": "DAD signal / mA.U.",
#                     "extcoef": 33.0
#                 },
#                 "B": {
#                     "y_label": "Solvent B Gradient %"
#                 }
#             },
#             "ams39-run1": { }, "ams39-run2": { }}
#     raw data example:
#         ams39raw:{'ams39-run0':{'A':{'time':[0.0,39.99,6000]},'signal':[0,0.1,...]},'B':{'time':},'ams39-run1'}
#     when load in to Data Class,
#     index is loaded to data.index
#     meta information is loaded to data.experiment = {'ams39':{}}
#     raw data is loaded to data.experiment_raw = {'ams39':{}}  !!! caution: 'raw' tag is discarded during loading.
#     """
#     def __init__(self,data_index):
#         self.index = data_index
#         self.experiment = {} # {ams0:{ams0-run1:{date: ,time: , A:{}}}}
#         self.experiment_to_save = {}
#         self.experiment_raw = {}
#         self.experiment_load_hist = []
#         self.max_load = 200

#     def next_index(self,n):
#         entry = list(self.index.keys())
#         if not entry:
#             entry = ['ams0']
#         entry = sorted(entry, key=lambda x: int(x.split('-')[0][3:]), reverse=True)[0]
#         entry_start = int(entry.split('-')[0][3:])+1
#         new_entry_list=['ams'+str(i) for i in range(entry_start, entry_start+n)]
#         return new_entry_list
#     def next_run(self,index,n):
#         entry = list(self.experiment[index].keys())
#         if not entry:
#             entry_start = 0
#         else:
#             entry = sorted(entry, key=lambda x: int(x.split('-')[1][3:]), reverse=True)[0]
#             entry_start = int(entry.split('-')[1][3:])+1
#         new_entry_list=[index+'-run'+str(i) for i in range(entry_start, entry_start+n)]
#         return new_entry_list
#     def load_experiment(self,new):
#         if self.max_load < len(self.experiment.keys()):
#             to_delete =[]
#             for i in self.experiment_load_hist[0:100]:
#                 if i not in self.experiment_to_save.keys():
#                     del self.experiment[i]
#                     del self.experiment_raw[i]
#                     to_delete.append(i)
#             self.experiment_load_hist = [i for i in self.experiment_load_hist if i not in to_delete ]
#         new_load = list(set(new)-raw_data.experiment.keys())
#         if new_load:
#             with shelve.open(os.path.join(file_path,file_name)) as hd:
#                 for i in new_load:
#                     raw_data.experiment[i] = hd.get(i,{})
#                     raw_data.experiment_raw[i] = hd.get(i+'raw',{})
#                     self.experiment_load_hist.append(i)

# with shelve.open(os.path.join(file_path,file_name),writeback=False) as hd:
#     data_index = hd['index']
#     raw_data = Data(data_index)
