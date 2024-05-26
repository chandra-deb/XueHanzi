for char in hsk1.words:
        translations = ''
        for translation in char['translations']:
            translations += translation + ', '
        character = Character(
            hsk_serial=char["id"],
            character=char['hanzi'],
            pinyin=char['pinyin'],
            meaning=translations,
            tags='',
            hsk_level=1)
        db.session.add(character)

    for char in hsk2.words:
        translations = ''
        for translation in char['translations']:
            translations += translation + ', '
        character = Character(
            hsk_serial=char["id"],
            character=char['hanzi'],
            pinyin=char['pinyin'],
            meaning=translations,
            tags='',
            hsk_level=2)
        db.session.add(character)
