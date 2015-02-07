import datetime
from application import app
from application import db

## --------- Page ---------

class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    picture = db.Column(db.String(80))
    creation_date = db.Column(db.DateTime(), default=datetime.datetime.now)

    # Required for administrative interface
    def __str__(self):
        return str(self.title)
