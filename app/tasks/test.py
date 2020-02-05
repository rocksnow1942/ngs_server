from pptx import Presentation
from dateutil import parser
from datetime import datetime
import re
flag = "note"
regx = re.compile(f'(?P<pt><{flag}>)(.+)(?P<ft></{flag}>)')

date = re.compile("(?P<y>20\d{2}|\d{2})\W*(?P<m>[0]\d|1[0-2]|[1-9])\W*(?P<d>[0-2]\d|3[01]|\d)(?:\s*\((?P<author>[a-zA-Z\s]+)\))?")

date.search('20120103  ( ) ').groups()

parser.parse('11/01/2010')

int(2011)

ppt = Presentation('/Users/hui/Desktop/VEGF/RIC50 SELEX QC.pptx')
for slide in ppt.slides:
    temp = []
    for shape in slide.shapes:
        if hasattr(shape, "text") and shape.text.strip():
            temp.append((shape.text, shape.top))
    if not temp:
        temp.append(("No Title", 0))
    temp.sort(key=lambda x: x[1])
    title = temp[0][0]
    match = date.search(title)
    if match:
        y,m,d,author = match.groups()
    else:
        y,m,d,author = '2011',1,1,None
    y = '20'+y if len(y)==2 else y
    time = datetime(int(y),int(m),int(d))
    print(time,author)




datetime(20,1,1,)


uniTag = re.compile('<(?P<pt>tag|note|flag)>(?P<content>.*)</(?P=pt)>')
uniTag.search(notes)

a=uniTag.findall(notes)
dict(a)
a

uniTag.findall("<flag></flag>")

uniTag.findall('s')

list(filter(lambda x:x[0]=='tag',a))
a
tag = re.compile('<tag>(.*)</tag>')
note = re.compile('<note>(.*)</note>')
flag = re.compile('(?P<pt><flag>)(?P<content>.*)(?P<ft></flag>)')
notes = '<tag>this is a tag,</tag>\n<note>this is a note,</note><a>aga</a>'
re.sub(regx,'\g<pt>'+'new'+'\g<ft>',notes)
regx.search(notes)
flag.search("<flag> </flag>").group('content')

n = tag.search(notes)
n
n and n.group(1)
print(tag.search("<tag></tag>").group(1))
tag.search("<tag></tag>").group(1)
" a".strip()

flag.search(notes)
tag.search(notes)
note.search(notes).group(1)

notes.replace(note,'new')


ppt=Presentation("/Users/hui/Desktop/Apt Quant.pptx")
ppt.core_properties.revision
s1 = ppt.slides[0]
s2 = ppt.slides[3]
s1.has_notes_slide
s2.has_notes_slide
s1.notes_slide


text_frame = s1.notes_slide.notes_text_frame
text_frame.text
s2.notes_slide.notes_text_frame.text = '<tag>this is a tag,</tag>\n<note>this is a note,</note>'
s2.notes_slide.notes_text_frame.text

ppt.save("/Users/hui/Desktop/Apt Quant.pptx")
