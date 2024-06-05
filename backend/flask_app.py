from bs4 import BeautifulSoup
from flask import Flask, redirect, render_template, jsonify, session, url_for
from flask_sqlalchemy import SQLAlchemy
from unidecode import unidecode
from flask import request
import hsk1, hsk2, hsk3, hsk4, hsk5, hsk6
import random
import requests

app = Flask(__name__)

key_of_prev_url_of_reading = "previous_url_of_reading"
key_of_prev_url_of_writing = "previous_url_of_writing"


def get_prev_url(reading=False, writing=False):
    if reading:
        return session.get(key_of_prev_url_of_reading, "/")
    elif writing:
        return session.get(key_of_prev_url_of_writing, "/")
    return "/"


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///characters.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "your_secret_key_here"

db = SQLAlchemy(app=app)

character_tags = db.Table(
    "character_tags",
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
    db.Column(
        "character_id", db.Integer, db.ForeignKey("character.id"), primary_key=True
    ),
)


class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hsk_serial = db.Column(db.Integer)
    hsk_level = db.Column(db.Integer)
    character = db.Column(db.String(8))
    pinyin = db.Column(db.String(50))
    no_tone_pinyin = db.Column(db.String(50))
    meaning = db.Column(db.String(200))
    can_write = db.Column(db.Boolean, default=False)
    is_known = db.Column(db.Boolean, default=False)
    tags = db.relationship(
        "Tag",
        secondary=character_tags,
        lazy="subquery",
        backref=db.backref("characters", lazy=True),
    )

    def __init__(self, hsk_serial, hsk_level, character, pinyin, meaning, tags):
        self.hsk_serial = hsk_serial
        self.hsk_level = hsk_level
        self.character = character
        self.meaning = meaning
        self.pinyin = pinyin
        self.no_tone_pinyin = unidecode(pinyin)
        self.tags = [Tag(name=tag_name) for tag_name in tags]

    def to_dict(self):
        return {
            "id": self.id,
            "hsk_serial": self.hsk_serial,
            "hsk_level": self.hsk_level,
            "character": self.character,
            "pinyin": self.pinyin,
            "meaning": self.meaning,
            "can_write": self.can_write,
            "is_known": self.is_known,
        }


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))

    def __init__(self, name):
        self.name = name

    def character_count(self):
        return len(self.characters)

    def can_write_count(self):
        return len([c for c in self.characters if c.can_write])

    def known_count(self):
        return len([c for c in self.characters if c.is_known])

    def not_marked_count(self):
        return len([c for c in self.characters if not c.is_known and not c.can_write])

    def characters_can_write(self):
        return [c for c in self.characters if c.can_write]

    def characters_known(self):
        return [c for c in self.characters if c.is_known]

    def characters_not_marked(self):
        return [c for c in self.characters if not c.is_known and not c.can_write]


class SubTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    tag_id = db.Column(db.Integer, db.ForeignKey("tag.id"))
    tag = db.relationship("Tag", backref=db.backref("subtags", lazy=True))

    def __init__(self, name, tag):
        self.name = name
        self.tag = tag


def initialize_database():
    count = 0
    with app.app_context():
        db.create_all()
        count += 1
        for level in range(1, 7):
            if level == 1:
                words = hsk1.words
            elif level == 2:
                words = hsk2.words
            elif level == 3:
                words = hsk3.words
            elif level == 4:
                words = hsk4.words
            elif level == 5:
                words = hsk5.words
            elif level == 6:
                words = hsk6.words

            for char in words:
                translations = ""
                for translation in char["translations"]:
                    translations += translation + ", "
                character = Character(
                    hsk_serial=char["id"],
                    character=char["hanzi"],
                    pinyin=char["pinyin"],
                    meaning=translations,
                    tags="",
                    hsk_level=level,
                )
                db.session.add(character)

        print(count)

        db.session.commit()


@app.route("/login", methods=["GET", "POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    if username == "admin" and password == "learningisearning1":
        session["username"] = username  # Add the user to the session
        return redirect(url_for("home"))
    else:
        return render_template("login_page.html")


from flask import request, redirect, url_for


@app.before_request
def require_login():
    allowed_routes = ["login"]
    if "username" not in session and request.endpoint not in allowed_routes:
        return redirect(url_for("login"))


@app.route("/")
def home():
    page_number = 1
    page = request.args.get("page", page_number, type=int)
    per_page = 30
    characters = db.session.query(Character).paginate(page=page, per_page=per_page)
    # for chara in characters.items:
    # print("Character: ", chara.tags)
    # print("Tags: ", chara.tags)
    return render_template(
        "index.html",
        title="Home",
        characterList=characters.items,
        next_page_number=page_number + 1,
        prev_page_number=page_number - 1,
    )


@app.route("/wchars")
def writablechars():
    session[key_of_prev_url_of_writing] = request.url

    characters = db.session.query(Character).filter_by(can_write=True).all()
    return render_template(
        "wchars.html",
        title="Writable Characters",
        characterList=characters,
        charsLength=len(characters),
    )


@app.route("/kpractice/<string:condition>", methods=["GET"])
def kpractice(condition):

    tag_ids = request.args.getlist("tags")
    error_msg = None
    character = None
    if condition == "tag-all-chars":
        error_msg, character = randomCharacterFrom(tag_ids)
    else:
        error_msg, character = randomCharacterFrom(tag_ids, is_known=True)
    return render_template(
        "known_practice.html",
        character=character,
        error_msg=error_msg,
        prev_url=get_prev_url(reading=True),
    )


# Test Purpose
@app.route("/wpractice/<string:condition>", methods=["GET"])
def wpractice(condition):
    session[key_of_prev_url_of_writing] = request.url

    tag_ids = request.args.getlist("tags")
    error_msg = None
    character = None
    if condition == "tag-all-chars":
        error_msg, character = randomCharacterFrom(tag_ids)
    else:
        error_msg, character = randomCharacterFrom(tag_ids, can_write=True)

    # writable_characters = db.session.query(Character).filter_by(can_write=True).all()
    # character = random.choice(writable_characters)

    urls = []
    if character:
        urls = char_link_extractor(character)
    return render_template(
        "writing_practice.html",
        title="Practice",
        img_urls=urls,
        character=character,
        error_msg=error_msg,
    )


def randomCharacterFrom(tag_ids, can_write=False, is_known=False):
    practice_characters = []
    if len(tag_ids) == 0:
        if can_write:
            practice_characters = (
                db.session.query(Character).filter_by(can_write=True).all()
            )
        elif is_known:
            practice_characters = (
                db.session.query(Character).filter_by(is_known=True).all()
            )
    else:
        for tag_id in tag_ids:
            tag = db.session.query(Tag).filter_by(id=tag_id).first()
            if tag:
                if can_write:
                    chars = (
                        db.session.query(Character)
                        .join(Character.tags)
                        .filter(Tag.id.in_(tag_ids))
                        .filter(Character.can_write == True)
                        .all()
                    )

                elif is_known:
                    chars = (
                        db.session.query(Character)
                        .join(Character.tags)
                        .filter(Tag.id.in_(tag_ids))
                        .filter(Character.is_known == True)
                        .all()
                    )
                # This else clause will return all the character for practice within the tag
                else:
                    chars = (
                        db.session.query(Character)
                        .join(Character.tags)
                        .filter(Tag.id.in_(tag_ids))
                        .all()
                    )

                practice_characters.extend(chars)
    error_msg = "No characters found"
    character = ""
    try:
        character = random.choice(practice_characters)
        error_msg = None

    except IndexError:
        pass
    return error_msg, character


def char_link_extractor(character) -> list:
    urls = []
    characters = []
    for single in character.character:
        if single not in characters:
            characters.append(single)
            urls.append(
                "/strokeorderDownloads/hsk{}/{}.png".format(character.hsk_level, single)
            )
            urls.append(
                "/strokeorderDownloads/hsk{}/sheets/{}-sheet.png".format(
                    character.hsk_level, single
                )
            )
    return urls


# @app.route('/wpractice')
# def wpractice():
#     writable_characters = db.session.query(Character).filter_by(can_write=True).all()
#     character = random.choice(writable_characters)

#     urls = []
#     characters =[]

#     for single in character.character:
#         if(single not in characters):
#             characters.append(single)

#             url = f"https://www.strokeorder.com/chinese/{single}"
#             response = requests.get(url)
#             soup = BeautifulSoup(response.text, 'html.parser')


#             # for how to write
#             div = soup.find_all('div', class_='stroke-article-content')
#             div_sheet = div[1]
#             div_char = div[0]
#             if div_char is not None:
#                 img = div_char.find('img')
#                 if img is not None:
#                     urls.append(f"https://www.strokeorder.com{img['src']}")
#             # for character sheet
#             if div_sheet is not None:
#                 img = div_sheet.find('img')
#                 if img is not None:
#                     urls.append(f"https://www.strokeorder.com{img['src']}")
#     return render_template('writing_practice.html',
#                         title='Practice' ,
#                         img_urls=urls, character=character)


@app.route("/character/<character>")
def get_character_image(character):

    url = f"https://www.strokeorder.com/chinese/{character}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # for character sheet
    div = soup.find("div", class_="stroke-article-content")
    if div is not None:
        img = div.find("img")
        if img is not None:
            print(img["src"])

    # How to write character

    div = soup.find("div", class_="stroke-article-content")
    if div is not None:
        img = div.find("img")
        if img is not None:
            return jsonify({"image_src": f"https://www.strokeorder.com{img['src']}"})

    return jsonify({"error": "Image not found"}), 404

    # @app.route('how_to_write:<string:character>')
    # def how_to_write(character):

    """<div class="stroke-article-content">
<img src="/assets/bishun/stroke/20320.png" alt="你 Stroke Order Diagrams" title="你 Stroke Order Diagrams">
</div>"""
    # return render_template('how_to_write.html', character=character)


# generate a route for modifying can_write attribute
@app.route("/update_data/<int:char_id>", methods=["POST"])
def update_data(char_id):
    can_write = "canwrite" in request.form
    can_not_write = "cannotwrite" in request.form
    known = "known" in request.form
    dknown = "dknown" in request.form
    character = db.session.query(Character).get(char_id)
    if can_write:
        character.can_write = can_write
    if can_not_write:
        character.can_write = False
    if known:
        character.is_known = known
    if dknown:
        character.is_known = False
    db.session.commit()

    return redirect(request.referrer)


@app.route("/kchars")
def knownchars():
    session[key_of_prev_url_of_reading] = request.url
    characters = db.session.query(Character).filter_by(is_known=True).all()
    tags = db.session.query(Tag).all()
    return render_template(
        "kchars.html",
        title="Known Characters",
        characterList=characters,
        charsLength=len(characters),
        tags=tags,
    )


@app.route("/search", methods=["GET", "POST"])
def search():

    if request.method == "POST":
        query = request.form.get("query").strip()
        session["query"] = query  # Store the query in the session
    query = session.get("query", "")

    char_results = [
        char.to_dict()
        for char in Character.query.filter(
            Character.character.like(f"%{query}%")
        ).limit(10)
    ]

    if char_results == None:
        char_results = []

    pinyin_results = [
        char.to_dict()
        for char in Character.query.filter(
            Character.no_tone_pinyin.like(f"%{query}%")
        ).limit(10)
    ]
    if pinyin_results == None:
        pinyin_results = []

    meaning_results = [
        char.to_dict()
        for char in Character.query.filter(Character.meaning.like(f"%{query}%")).limit(
            10
        )
    ]
    if meaning_results == None:
        meaning_results = []

    return render_template(
        "search_results.html",
        char_results=char_results,
        pinyin_results=pinyin_results,
        meaning_results=meaning_results,
    )


@app.route("/showcharsheet/<string:character>")
def showcharsheet(character):
    c = db.session.query(Character).filter_by(character=character).first()

    img_urls = char_link_extractor(c)
    print(img_urls)
    return render_template("show_char_sheet.html", img_urls=img_urls)


@app.route("/tags")
def tags():
    session[key_of_prev_url_of_reading] = request.url
    session[key_of_prev_url_of_writing] = request.url
    tags = Tag.query.all()
    return render_template("tags.html", tags=tags)


@app.route("/tags/<int:tag_id>")
def tag_characters(tag_id):
    tag = Tag.query.get(tag_id)
    session[key_of_prev_url_of_reading] = request.url

    can_read_characters = [char for char in tag.characters if char.is_known]
    can_write_characters = [char for char in tag.characters if char.can_write]
    both_characters = [
        char for char in tag.characters if char.is_known and char.can_write
    ]
    total_characters = tag.characters
    totally_new_characters = [
        char
        for char in tag.characters
        if char.is_known == False and char.can_write == False
    ]  # Assuming 'is_new' attribute exists

    return render_template(
        "tag_characters.html",
        tag=tag,
        can_read_characters=can_read_characters,
        can_write_characters=can_write_characters,
        both_characters=both_characters,
        total_characters=total_characters,
        totally_new_characters=totally_new_characters,
    )

    # return render_template("tag_characters.html", tag=tag)


@app.route("/add_tag", methods=["POST"])
def add_tag():
    # character = request.form['character']
    add_tag_name = request.form["add-tag"].strip()
    remove_tag_name = request.form["remove-tag"].strip()

    # Get the character and tag from the database
    if len(add_tag_name) > 4:
        # char = Character.query.filter_by(character=character).first()
        tag_to_add = Tag.query.filter_by(name=add_tag_name).first()
        if tag_to_add is None:
            tag = Tag(name=add_tag_name)
            db.session.add(tag)
    if len(remove_tag_name) > 4:
        tag_to_remove = Tag.query.filter_by(name=remove_tag_name).first()
        # If the tag doesn't exist, create it
        if tag_to_remove:
            db.session.delete(tag_to_remove)

    # Add the tag to the character and commit the changes
    # char.tags.append(tag)
    db.session.commit()

    return redirect(url_for("tags"))


@app.route("/character/<int:character_id>/tags")
def get_character_tags(character_id):
    character = Character.query.get(character_id)
    return render_template("character_tags.html", character=character)


from flask import request, jsonify


@app.route("/character/<int:character_id>/update_tags", methods=["POST"])
def update_character_tags(character_id):
    character = Character.query.get(character_id)
    if character is None:
        return "Character not found", 404

    data = request.get_json()
    new_tags_id = data.get("tags", [])
    print("New Tags")
    print(new_tags_id)

    # Remove all existing tags
    character.tags = []

    # Add new tags
    for tag_id in new_tags_id:
        tag = Tag.query.get(tag_id)
        if tag is not None:
            character.tags.append(tag)

    db.session.commit()

    return jsonify({"message": "Tags updated successfully"})


@app.route("/charTags/<int:char_id>")
def charTags(char_id):
    character = db.session.query(Character).get(char_id)
    tags = db.session.query(Tag).all()
    other_tags = [tag for tag in tags if tag not in character.tags]
    return render_template("char_tags.html", character=character, other_tags=other_tags)


@app.route("/search-for-tag/<int:tag_id>", methods=["GET", "POST"])
def search_for_tag(tag_id):
    tag = Tag.query.get(tag_id)

    if request.method == "POST":
        query = request.form.get("query").strip()
        session["query"] = query  # Store the query in the session
    query = session.get("query", "")

    def get_results(query, attribute):
        return [
            {**char.to_dict(), "in_tag": char in tag.characters}
            for char in Character.query.filter(
                getattr(Character, attribute).like(f"%{query}%")
            ).limit(10)
        ]

    char_results = get_results(query, "character")
    pinyin_results = get_results(query, "no_tone_pinyin")
    meaning_results = get_results(query, "meaning")

    return render_template(
        "search_for_tag_page.html",
        char_results=char_results,
        pinyin_results=pinyin_results,
        meaning_results=meaning_results,
        tag=tag,
    )


@app.route("/attachTag/<int:char_id>/<int:tag_id>")
def attachTag(char_id, tag_id):
    character = db.session.query(Character).get(char_id)
    tag = db.session.query(Tag).get(tag_id)
    if tag not in character.tags:
        character.tags.append(tag)
        db.session.commit()
    return redirect(url_for("search_for_tag", tag_id=tag_id))


@app.route("/removeTag/<int:char_id>/<int:tag_id>")
def removeTag(char_id, tag_id):
    character = db.session.query(Character).get(char_id)
    tag = db.session.query(Tag).get(tag_id)
    if tag in character.tags:
        character.tags.remove(tag)
        db.session.commit()
    return redirect(url_for("search_for_tag", tag_id=tag_id))


@app.route("/add_bulk_char_in_tag/<int:tag_id>", methods=["GET", "POST"])
def add_bulk_char_in_tag(tag_id):
    tag = db.session.query(Tag).get(tag_id)
    if request.method == "POST":
        characters = request.form["characters"].split()
        unknown_chars = []
        total_characters_length = len(characters)
        already_in_tag_characters = []
        newly_added_characters = []
        for character in characters:
            char = db.session.query(Character).filter_by(character=character).first()
            if char:
                if char not in tag.characters:
                    tag.characters.append(char)
                    newly_added_characters.append(character)
                else:
                    already_in_tag_characters.append(character)
            else:
                unknown_chars.append(character)
        db.session.commit()
        return render_template(
            "bulk_char_add_report.html",
            tag=tag,
            total_characters_length=total_characters_length,
            unknown_chars=unknown_chars,
            already_in_tag_characters=already_in_tag_characters,
            newly_added_characters=newly_added_characters,
        )
        # return redirect(url_for("tag_characters", tag_id=tag_id))
    return render_template("add_bulk_chars_in_tag.html", tag=tag)


if __name__ == "__main__":
    # initialize_database()
    app.run(debug=True)
