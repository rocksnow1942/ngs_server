from os import path
import platform


localmode=False


systemname = platform.node()
if localmode:
    _file_path = path.dirname(__file__)
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
