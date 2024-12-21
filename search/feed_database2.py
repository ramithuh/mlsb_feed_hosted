# feed_database2.py

#!/usr/bin/env python
# coding: utf-8

import peewee
from datetime import datetime

# Database configuration
db = peewee.SqliteDatabase('../feed_database2.db')

class BaseModel(peewee.Model):
    class Meta:
        database = db

class Post(BaseModel):
    uri = peewee.CharField(index=True)
    cid = peewee.CharField()
    reply_parent = peewee.CharField(null=True, default=None)
    reply_root = peewee.CharField(null=True, default=None)
    indexed_at = peewee.DateTimeField(default=datetime.utcnow)

def check_feed_for_cid(target_cid: str, limit: int = 150) -> None:
    """
    Example function that searches for a given CID in the latest posts.
    """
    try:
        with db.connection_context():
            posts = Post.select().order_by(
                Post.cid.desc()
            ).order_by(
                Post.indexed_at.desc()
            ).limit(limit)

            for idx, post in enumerate(posts):
                if post.cid == target_cid:
                    print(f"Found post at position {idx + 1} in feed")
                    print(f"URI: {post.uri}")
                    print(f"Indexed At: {post.indexed_at}")
                    break
            else:
                print(f"CID {target_cid} not found in first {limit} posts")
    except Exception as e:
        print(f"Error checking feed: {str(e)}")
    finally:
        if not db.is_closed():
            db.close()

# Initialize DB and create tables if they don't exist yet
with db.connection_context():
    db.create_tables([Post])