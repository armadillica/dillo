from application import app
from application import db

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    value = db.Column(db.Text(), nullable=False)
    data_type = db.Column(db.String(128), nullable=False)

    def __str__(self):
        return "<{0}>".format(str(self.name))
