from os import path
import platform

localmode=False


systemname = platform.node()

if localmode:
    file_save_location =  path.join(path.dirname(__file__),'cache')
    temp_position = file_save_location

elif systemname.startswith('huis-mac-mini'):
    file_save_location = '/Users/hui/Cloudstation/R&D/Users/Hui Kang/Scripts/plojo/plojo/data'
    temp_position=path.join(file_save_location,'temp')
elif systemname.startswith('huis-mbp'):
    file_save_location = '/Users/hui/Aptitude_Cloud/Aptitude Users/R&D/Users/Hui Kang/Scripts/plojo/plojo/data'
    temp_position=path.join(file_save_location,'temp')
elif systemname == 'plojo':
    file_save_location = '/home/hui/AptitudeUsers/R&D/Users/Hui Kang/Scripts/plojo/plojo/data'
    temp_position= '/home/hui/AptitudeUsers/R&D Backup/Plojo backup/temp'
else:
    file_save_location =  path.join(path.dirname(__file__),'data')
    temp_position = "C:\\Users\\aptitude\\Aptitude-Cloud\\R&D Backup\\Plojo backup\\temp"


file_name = 'plojo_data'
