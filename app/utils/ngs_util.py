from itertools import islice
import os


def reverse_comp(s):
    s=s.upper()
    comp=''.join(map(lambda x:dict(zip('ATCGN','TAGCN'))[x]  ,s))
    return comp[::-1]

def file_blocks(files, size=65536):
    while True:
        b = files.read(size)
        if not b: break
        yield b

def check_file_reverse_comp(f1,f2):
    nonrevcount = 0
    for l1,l2 in islice(zip(f1,f2),1,800,4):
        l1_ = l1.decode('utf-8')
        l2_=l2.decode('utf-8')
        if reverse_comp(l1_.strip())!=l2_.strip():
            nonrevcount+=1
    if nonrevcount>50:
        return False
    return True

def create_folder_if_not_exist(savefolder):
    if not os.path.isdir(savefolder):
        os.makedirs(savefolder)


def convert_id_to_string(id,base=''):
    c='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    l = id//36
    r = id%36
    base = c[r] + base
    if l:
        return convert_id_to_string(l,base)
    return base

def convert_string_to_id(s):
    c='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    result = 0
    for k,i in enumerate(s[::-1]):
        result = result + c.index(i.upper())*(36**k)
    return result
