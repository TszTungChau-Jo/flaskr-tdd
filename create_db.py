# create_db.py


from project.app import app, db
from project.models import Post


with app.app_context():
    # create the database and the db table
    db.create_all()

    # commit the changes
    db.session.commit()