from app import Character, db
from app import app
import hsk1, hsk2, hsk3, hsk4, hsk5, hsk6


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
