from app import db
from flask import render_template, flash, redirect,url_for,request,current_app,jsonify
from flask_login import current_user,login_required
from app.API import bp
from app.models import AccessLog,Selection, Rounds, models_table_name_dictionary, SeqRound, Project, PPT, Slide, Task, NGSSampleGroup, Analysis


@bp.route('/testapi', methods=['POST','GET'])
def testapi():
    data = request.json
    print(data)
    return jsonify(data)
