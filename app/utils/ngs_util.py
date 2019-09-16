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


def lev_distance(s1, s2, threshold=1000):
    """
    calculate diagonally.stop at threshold. fastest.
    """
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    l1 = len(s1)
    vertical = [0]
    horizontal = [0]
    for i in range(l1):
        char1 = s1[i]
        char2 = s2[i]
        newvertical = [i+1]
        newhorizontal = [i+1]
        for k in range(i):
            if char1 == s2[k]:
                newvertical.append(vertical[k])
            else:
                newvertical.append(
                    1+min(newvertical[-1], vertical[k], vertical[k+1]))
            if char2 == s1[k]:
                newhorizontal.append(horizontal[k])
            else:
                newhorizontal.append(
                    1+min(newhorizontal[-1], horizontal[k], horizontal[k+1]))
        last = vertical[-1] if char1 == char2 else (
            1+min(newvertical[-1], newhorizontal[-1], vertical[-1]))
        newhorizontal.append(last)
        newvertical.append(last)
        currentmin = min(min(newhorizontal), min(newvertical))
        if currentmin > threshold:
            return currentmin
        vertical, horizontal = newvertical, newhorizontal
    horizontal.append(last)
    for index2, char2 in enumerate(s2[l1:]):
        newhorizontal = [index2+l1+1]
        for index1, char1 in enumerate(s1):
            if char1 == char2:
                newhorizontal.append(horizontal[index1])
            else:
                newhorizontal.append(1 + min((horizontal[index1],
                                              horizontal[index1 + 1],
                                              newhorizontal[-1])))
        currentmin = min(newhorizontal)
        if currentmin > threshold:
            return currentmin
        horizontal = newhorizontal
    return horizontal[-1]
