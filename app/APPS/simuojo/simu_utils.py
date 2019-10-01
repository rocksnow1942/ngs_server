from os import path
import platform


localmode=False


systemname = platform.node()
if localmode:
    file_save_location = path.join('/Users/hui/Scripts/plojo_app/plojo','data')
elif systemname.startswith('huis-mac-mini'):
    file_save_location = '/Users/hui/Cloudstation/R&D/Users/Hui Kang/Scripts/plojo/plojo/data'

elif systemname.startswith('huis-mbp'):
    file_save_location = '/Users/hui/Aptitude_Cloud/Aptitude Users/R&D/Users/Hui Kang/Scripts/plojo/plojo/data'
elif systemname == 'plojo':
    file_save_location = '/home/hui/AptitudeUsers/R&D/Users/Hui Kang/Scripts/plojo/plojo/data'
else:
    file_save_location = r"C:\Users\aptitude\Aptitude-Cloud\R&D\Users\Hui Kang\Scripts\plojo\plojo\data"
file_name = 'plojo_data'
