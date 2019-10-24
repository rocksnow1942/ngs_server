import sys
from pathlib import PurePath
filepath = PurePath(__file__).parent.parent.parent
sys.path.append(str(filepath))
from app.models import KnownSequence
from app import create_app
from app import db
from app.utils.analysis import KnownSeq

"""
import known_sequence from csv to known_sequence table; run from ngs_server folder; use venv
"""
knownseq_file_path = "/home/hui/AptitudeUsers/R&D/Users/Hui Kang/known_seq.csv"


app = create_app(keeplog=False)
app.app_context().push()




def add_known_sequence_to_database(filepath):
    ks = KnownSeq(filepath)
    for name in ks.names:
        seq = ks[name]
        new = KnownSequence(sequence_name=name,rep_seq=seq.rep_seq(),target=seq.target,note=seq.note)
        try:
            db.session.add(new)
            db.session.commit()
            print('Add {}-{}.'.format(new.sequence_name,new.id))
        except Exception as e:
            db.session.rollback()
            print('Fail to add {} - {}.'.format(name,e))

if __name__ == "__main__":
    add_known_sequence_to_database(knownseq_file_path)
