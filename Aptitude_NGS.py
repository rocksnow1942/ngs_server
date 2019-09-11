from app import create_app,db
from app.models import User,Selection, Rounds,Primers,SeqRound,Sequence

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Selection': Selection,'Rounds':Rounds, 
    'Primers':Primers,'SeqRound':SeqRound,'Sequence':Sequence}
