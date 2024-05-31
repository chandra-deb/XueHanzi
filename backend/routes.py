from flask import render_template
from backend.flask_app import app, db, Character


@app.route('/')
def home():
    characters = db.session.query(Character).all()
    return render_template('index.html', title='Home' , characterList=characters)

# @app.route('/')
# def writablechars():
#     characters = db.session.query(Character).filter_by(can_write=True).all()
#     return render_template('writeable_chars.html', title='Writable Characters' , characterList=characters)
