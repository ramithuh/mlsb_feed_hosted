# new_database.py

import peewee
from datetime import datetime

new_db = peewee.SqliteDatabase('content_database.db')

class BaseContentModel(peewee.Model):
    class Meta:
        database = new_db

class PostContent(BaseContentModel):
    cid = peewee.CharField(unique=True)
    uri = peewee.CharField(index=True)         # We'll store 'at://...' here
    username = peewee.CharField(null=True)     # The handle, e.g. 'ramith.fyi'
    content_text = peewee.TextField(null=True) # The text of the post
    created_at = peewee.DateTimeField(default=datetime.utcnow)

# Initialize DB and create tables if they don't exist yet
with new_db.connection_context():
    new_db.create_tables([PostContent])
