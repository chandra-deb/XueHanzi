from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
import hsk1, hsk2, hsk3, hsk4, hsk5, hsk6


from flask_sqlalchemy import SQLAlchemy

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

# Create a new Tag
# tag = Tag(name='Tag Name')
# db.session.add(tag)
# db.session.commit()

# # Create a new SubTag associated with a Tag
# tag = Tag.query.filter_by(name='Tag Name').first()
# subtag = SubTag(name='SubTag Name', tag=tag)
# db.session.add(subtag)
# db.session.commit()



""" characterList = [{"character": "你", "pinyin": "nǐ", "meaning": "you"}, 
                 {"character": "好", "pinyin": "hǎo", "meaning": "good"},
                 {"character": "吗", "pinyin": "ma", "meaning": "question particle"},
                 {"character": "我", "pinyin": "wǒ", "meaning": "I"},
                 {"character": "很", "pinyin": "hěn", "meaning": "very"},
                 {"character": "也", "pinyin": "yě", "meaning": "also"},
                 {"character": "是", "pinyin": "shì", "meaning": "to be"},
                 {"character": "谢谢", "pinyin": "xièxiè", "meaning": "thank you"},
                 {"character": "不客气", "pinyin": "bú kèqì", "meaning": "you're welcome"},
                 {"character": "再见", "pinyin": "zàijiàn", "meaning": "goodbye"},
                 {"character": "对不起", "pinyin": "duìbuqǐ", "meaning": "I'm sorry"},
                 {"character": "没关系", "pinyin": "méi guānxi", "meaning": "it's okay"},
                 {"character": "请问", "pinyin": "qǐngwèn", "meaning": "excuse me"},
                 {"character": "请坐", "pinyin": "qǐng zuò", "meaning": "please sit"},
                 {"character": "请喝茶", "pinyin": "qǐng hē chá", "meaning": "please drink tea"},
                 {"character": "请问你叫什么名字", "pinyin": "qǐngwèn nǐ jiào shénme míngzì", "meaning": "what is your name"},
                 {"character": "我叫", "pinyin": "wǒ jiào", "meaning": "my name is"},
                 {"character": "你叫什么名字", "pinyin": "nǐ jiào shénme míngzì", "meaning": "what is your name"},
                 {"character": "你贵姓", "pinyin": "nǐ guìxìng", "meaning": "what is your surname"},]
 """
with app.app_context():
    db.create_all()
    
    for level in range(1, 7):
        if level == 1:
            words = hsk1.words
        elif level == 2:
            words = hsk2.words
        elif level == 3:
            words = hsk3.words
        elif level == 4:
            word = hsk4.words
        elif level == 5:
            words = hsk5.words
        elif level == 6:
            words = hsk6.words

        for char in words:
            translations = ''
            for translation in char['translations']:
                translations += translation + ', '
            character = Character(
                hsk_serial=char["id"],
                character=char['hanzi'],
                pinyin=char['pinyin'],
                meaning=translations,
                tags='',
                hsk_level=level)
            db.session.add(character)


    db.session.commit() 



@app.route('/')
def home():
    characters = db.session.query(Character).all()
    return render_template('index.html', title='Home' , characterList=characters)



if __name__ == '__main__':
    
    app.run(debug=True)

