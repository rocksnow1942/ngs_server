running_log = "/Users/hui/Desktop/log.txt"

from datetime import datetime
class FileLogger():
    def __init__(self, running_log=""):

        self.running_log = running_log

    @property
    def time(self):
        return datetime.now().strftime('%y/%m/%d %H:%M:%S')

    def write_log(self, content):
        with open(self.running_log, 'a') as f:
            f.write(f"{self.time} - " + content+'\n')

logger = FileLogger(running_log=running_log)
import time,os
for i in range(100):
    time.sleep(1)
    logger.write_log(f'test msg {i} - {os.getpid()}')