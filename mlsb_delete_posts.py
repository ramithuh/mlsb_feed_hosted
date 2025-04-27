import os
import re
import csv
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import peewee
import streamlit as st
from atproto import Client

###############################################################################
# Configuration                                                                
###############################################################################
DB_PATH = os.getenv("FEED_DB_PATH", "feed_database2.db")          # Bluesky desktop feed DB
LOG_PATH = os.getenv("DELETED_TSV_PATH", "deleted_posts.tsv")     # where deletions are logged

###############################################################################
# Database models                                                              
###############################################################################

db = peewee.SqliteDatabase(
    DB_PATH,
    pragmas={
        "journal_mode": "wal",
        "cache_size": -1024 * 64,  # 64 MB page cache
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
# Helpers                                                                      
###############################################################################

def get_client() -> Client:
    """Return a logged‑in atproto.Client instance."""
    client = Client()
    handle = st.secrets.get("bsky_handle", os.getenv("BSKY_HANDLE"))
    app_pass = st.secrets.get("bsky_app_password", os.getenv("BSKY_APP_PASS"))
    if not (handle and app_pass):
        st.error("Bluesky credentials missing. Set env vars or secrets.toml.")
        st.stop()
    client.login(handle, app_pass)
    return client


def convert_web_url_to_at_uri(web_url: str) -> Optional[str]:
    """Translate a Bluesky post URL into an AT URI."""
    pattern = r"https://bsky\.app/profile/([^/]+)/post/([^/]+)"
    if match := re.match(pattern, web_url.strip()):
        handle, post_id = match.groups()
        return f"at://{handle}/app.bsky.feed.post/{post_id}"
    return None

# --------------------------------------------------------------------------- #
# Deletion helpers                                                             #
# --------------------------------------------------------------------------- #

def delete_post_by_cid(post_cid: str) -> int:
    """Delete row(s) whose CID matches *post_cid*. Returns count."""
    with db.connection_context():
        return Post.delete().where(Post.cid == post_cid).execute()


def log_deletion(web_url: str, cid: str, did: str, text: str) -> None:
    """Append tab‑separated deletion record (timestamp | url | cid | did | text)."""
    row = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
        "web_url": web_url,
        "cid": cid,
        "did": did,
        "text": text.replace("\t", " ").replace("\n", " "),
    }
    file_exists = Path(LOG_PATH).exists()
    with open(LOG_PATH, "a", newline="", encoding="utf‑8") as fh:
        writer = csv.DictWriter(fh, fieldnames=row.keys(), delimiter="\t")
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

# --------------------------------------------------------------------------- #
# Addition helpers                                                             #
# --------------------------------------------------------------------------- #

def add_post_to_db(web_url: str) -> str:
    """Fetch a post by URL and insert into the local feed DB if absent.
    Returns a status string describing the outcome."""
    at_uri = convert_web_url_to_at_uri(web_url)
    if at_uri is None:
        return "Invalid Bluesky post URL."

    client = get_client()
    try:
        resp = client.get_post_thread(uri=at_uri)
    except Exception as exc:
        return f"Failed to fetch post: {exc}"

    post = resp.thread.post
    post_id = at_uri.split("/")[-1]

    # Build DID‑based URI so it matches the desktop DB schema
    uri = f"at://{post.author.did}/app.bsky.feed.post/{post_id}"
    cid = post.cid

    reply_parent = None
    reply_root = None
    if hasattr(post.record, "reply") and post.record.reply:
        reply_parent = post.record.reply.parent.uri if post.record.reply.parent else None
        reply_root = post.record.reply.root.uri if post.record.reply.root else None

    # created_at in ISO8601 with Z → convert to naive UTC datetime
    created_at = datetime.fromisoformat(post.record.created_at.replace("Z", "+00:00"))
    created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)

    with db.connection_context():
        if Post.select().where(Post.uri == uri).exists():
            return "Post already present in database."
        Post.create(
            uri=uri,
            cid=cid,
            reply_parent=reply_parent,
            reply_root=reply_root,
            indexed_at=created_at,
        )
    return "Post successfully added to database."

###############################################################################
# Streamlit UI                                                                 
###############################################################################

st.set_page_config(page_title="Bluesky Feed Cleaner / DB Helper", page_icon="🧹")
st.title("🧹 Bluesky Feed Cleaner & Adder")

# --------------------------- Deletion section --------------------------------#
st.subheader("Remove a post from your local DB")
remove_url = st.text_input("URL to remove", key="remove_url")
if st.button("Remove", key="remove_btn", type="primary"):
    if not remove_url.strip():
        st.warning("Please paste a URL.")
        st.stop()

    at_uri = convert_web_url_to_at_uri(remove_url)
    if at_uri is None:
        st.error("Not a valid Bluesky post URL.")
        st.stop()

    try:
        client = get_client()
        resp = client.get_post_thread(uri=at_uri)
        cid = resp.thread.post.cid
        text = resp.thread.post.record.text
        did = resp.thread.post.author.did
    except Exception as exc:
        st.error(f"Could not fetch post → {exc}")
        st.stop()

    deleted_n = delete_post_by_cid(cid)
    if deleted_n:
        log_deletion(remove_url, cid, did, text)
        st.success(f"Deleted {deleted_n} row(s). Logged to {LOG_PATH}.")
    else:
        st.info("No matching row found – nothing deleted.")

st.divider()

# ---------------------------- Addition section ------------------------------ #
st.subheader("Add a post back (or any new post) to your local DB")
add_url = st.text_input("URL to add", key="add_url")
if st.button("Add", key="add_btn", type="secondary"):
    if not add_url.strip():
        st.warning("Please paste a URL.")
        st.stop()

    result_msg = add_post_to_db(add_url)
    if result_msg.startswith("Post successfully"):
        st.success(result_msg)
    elif result_msg.startswith("Post already"):
        st.info(result_msg)
    else:
        st.error(result_msg)

st.caption(
    "Built with Streamlit · atproto · peewee · 🐍  |  Deletions logged to TSV; additions written straight to SQLite feed DB."
)