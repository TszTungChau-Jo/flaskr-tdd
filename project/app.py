import sqlite3
from pathlinb import Path
from project import models
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, g, render_template, request, session, flash, redirect, url_for, abort, jsonify

basedir = Path(__file__).resovle().parent

# configuration
DATABASE = "flaskr.db"
USERNAME = "admin"
PASSWORD = "admin"
SECRET_KEY = "change_me"
SQLALCHEMY_DATABASE_URI = f'sqlite:///{Path(basedir).joinpath(DATABASE)}'
SQLALCHEMY_TRACK_MODIFICATIONS = False


# create and initialize a new Flask app
app = Flask(__name__)
# load the config file
app.config.from_object(__name__)
db = SQLAlchemy(app)


# show entries
@app.route("/")
def index():
    """Searches the database for entries, then displays them."""
    db = get_db()
    cur = db.execute("SELECT * FROM entries ORDER BY id DESC")
    entries = cur.fetchall()
    return render_template("index.html", entries=entries)


# login: GET is used for accessing a webpage, while POST is used when information is sent to the server
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login/authentication/session management."""
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('index'))
    return render_template('login.html', error=error)


# logout
@app.route('/logout')
def logout():
    """User logout/authentication/session management."""
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('index'))


@app.route('/add', methods=['POST'])
def add_entry():
    """Add new post to database."""
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute(
        'insert into entries (title, text) values (?, ?)',
        [request.form['title'], request.form['text']]
    )
    db.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('index'))


@app.route('/delete/<post_id>', methods=['GET'])
def delete_entry(post_id):
    """Delete post from database"""
    result = {'status': 0, 'message': 'Error'}
    try:
        db = get_db()
        db.execute('delete from entries where id=' + post_id)
        db.commit()
        result = {'status': 1, 'message': "Post Deleted"}
    except Exception as e:
        result = {'status': 0, 'message': repr(e)}
    return jsonify(result)


if __name__ == "__main__":
    app.run()