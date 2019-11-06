from urllib.parse import urlparse
from datetime import datetime
import os

def parse_url_path(urlpath):
    """
    remove scheme and host name out from url.
    """
    pr = urlparse(urlpath)
    toremove = f"{pr.scheme}://{pr.netloc}/"
    return pr.geturl().replace(toremove, '', 1)


def get_part_of_day(hour):
    return ("morning" if 5 <= hour <= 11
            else
            "afternoon" if 12 <= hour <= 17
            else
            "evening" if 18 <= hour <= 22
            else
            "night")

def log_error(location):
    def decorator(func):
        def wrapped(*args,**kwargs):
            try:
                return func(*args,**kwargs)
            except Exception as e:
                with open(location,'a') as f:
                    f.write('='*50+'\n')
                    f.write(f'Time: {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}\n')
                    f.write(f'Error executing {func.__name__}:\nargs:{args}, kwargs:{kwargs}\n')
                    f.write(f'Reason: {e}\n')
                raise Exception  
        return wrapped 
    return decorator


def app_context_wrapper(app):
    def decorator(func):
        def wrapped(*args,**kwargs):
            with app.app_context():
                return func(*args,**kwargs)
        return wrapped       
    return decorator


def get_folder_size(start_path= '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size
