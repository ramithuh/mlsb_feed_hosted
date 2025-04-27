import os
import re
from datetime import datetime

import peewee
import streamlit as st
from atproto import Client

DB_PATH = os.getenv("FEED_DB_PATH", "feed_database2.db")

###############################################################################
# Database models                                                               
###############################################################################

db = peewee.SqliteDatabase(
    DB_PATH,
    pragmas={
        "journal_mode": "wal",      # concurrent reads/writes
        "cache_size": -1024 * 64,    # 64 MB page cache
    },
)


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Post(BaseModel):
    uri = peewee.CharField(index=True)
    cid = peewee.CharField()
    reply_parent = peewee.CharField(null=True, default=None)
    reply_root = peewee.CharField(null=True, default=None)
    indexed_at = peewee.DateTimeField(default=datetime.utcnow)


###############################################################################
# Helper functions                                                              
###############################################################################

def get_client() -> Client:
    """Return a logged‑in atproto.Client instance."""
    client = Client()
    handle = st.secrets["bsky_handle"]
    password = st.secrets["bsky_app_password"]
    client.login(handle, password)
    return client


def convert_web_url_to_at_uri(web_url: str) -> str | None:
    """Translate a Bluesky post URL into an AT URI understood by atproto."""
    pattern = r"https://bsky\.app/profile/([^/]+)/post/([^/]+)"
    if match := re.match(pattern, web_url):
        handle, post_id = match.groups()
        return f"at://{handle}/app.bsky.feed.post/{post_id}"
    return None


def delete_post(post_cid: str) -> int:
    """Remove rows matching *post_cid* from the database. Returns # deleted."""
    with db.connection_context():
        return Post.delete().where(Post.cid == post_cid).execute()


###############################################################################
# Streamlit UI                                                                  
###############################################################################

st.set_page_config(page_title="Bluesky Feed Cleaner", page_icon="🧹")
st.title("🧹 Bluesky Feed Cleaner")

web_url = st.text_input("Paste the Bluesky post URL you want to remove:")
clicked = st.button("Remove", type="primary")

if clicked:
    if not web_url.strip():
        st.warning("Please enter a URL first.")
        st.stop()

    at_uri = convert_web_url_to_at_uri(web_url)
    if at_uri is None:
        st.error("That doesn't look like a valid Bluesky post URL.")
        st.stop()

    # Fetch CID via atproto so we can match the DB row
    try:
        client = get_client()
        response = client.get_post_thread(uri=at_uri)
        post_cid = response.thread.post.cid
    except Exception as exc:
        st.error(f"Failed to fetch post details: {exc}")
        st.stop()

    # Delete from local database
    deleted = delete_post(post_cid)
    if deleted:
        st.success(f"Deleted {deleted} record(s) with CID {post_cid}.")
    else:
        st.info("No matching post found in the database.")

st.caption("Built with Streamlit · atproto · peewee · 🐍")
