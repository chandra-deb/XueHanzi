from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from unidecode import unidecode
from flask import request

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///characters.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app=app)

class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hsk_serial = db.Column(db.Integer)
    hsk_level = db.Column(db.Integer)
    character = db.Column(db.String(8))
    pinyin = db.Column(db.String(18))
    meaning = db.Column(db.String(200))
    can_write = db.Column(db.Boolean, default=False)
    is_known = db.Column(db.Boolean, default=False)
    tags = db.Column(db.String(500))

    def __init__(self, hsk_serial,hsk_level, character, pinyin, meaning, tags):
        self.hsk_serial = hsk_serial
        self.hsk_level = hsk_level
        self.character = character
        self.meaning = meaning
        self.pinyin = pinyin
        self.tags = tags
    




class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    def __init__(self, name):
        self.name = name

class SubTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'))
    tag = db.relationship('Tag', backref=db.backref('subtags', lazy=True))
    def __init__(self, name, tag):
        self.name = name
        self.tag = tag



@app.route('/')
def home():
    page_number = 1
    page = request.args.get('page', page_number, type=int)
    per_page = 30
    characters = db.session.query(Character).paginate(page=page, per_page=per_page)
    return render_template('index.html', title='Home', characterList=characters.items, next_page_number = page_number +1, prev_page_number = page_number -1)

@app.route('/wchars')
def writablechars():
    characters = db.session.query(Character).filter_by(can_write=True).all()
    return render_template('wchars.html',
                        title='Writable Characters' , 
                        characterList=characters)

#generate a route for modifying can_write attribute
@app.route('/update_data/<int:char_id>', methods=['POST'])
def update_data(char_id):
    can_write = 'canwrite' in request.form
    known = 'known' in request.form
    print(f"can write {request.form}")
    character = db.session.query(Character).get(char_id)
    character.can_write = can_write
    print(f"is known  {character.is_known}")
    character.is_known = known
    print(f"is known  {character.is_known}")
    db.session.commit()
    print(can_write,known)

    characters = db.session.query(Character).limit(30)
    return render_template('index.html',
                        title='Home Page', 
                        characterList=characters)
    

@app.route('/kchars')
def knownchars():
    characters = db.session.query(Character).filter_by(is_known=True).all()
    return render_template('kchars.html',
                        title='Known Characters' , 
                        characterList=characters)

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    char_results = [char for char in Character.query.filter(Character.character.like(f'%{query}%')).all()]
    print(char_results)
    pinyin_results =   [char for char in Character.query.filter(Character.pinyin.like(f'%{query}%')).all()]
    if(pinyin_results == None):
        pinyin_results = []
    meaning_results = [char for char in Character.query.filter(Character.meaning.like(f'%{query}%')).all()]
    if(meaning_results == None):
        meaning_results = []
    return render_template('search_results.html', char_results=char_results, pinyin_results=pinyin_results, meaning_results=meaning_results) 




if __name__ == '__main__':
    
    app.run(debug=True)

