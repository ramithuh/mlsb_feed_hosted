# data_update.py

import time
from feed_database2 import Post, db
from new_database import PostContent, new_db

from atproto import Client
from atproto_client.exceptions import RequestException
import time



def parse_at_uri(uri: str):
    """
    Example: at://some_handle/app.bsky.feed.post/3lds4r3qd7c2x
    Returns: (handle='some_handle', post_id='3lds4r3qd7c2x')
    """
    if uri.startswith("at://"):
        uri = uri.replace("at://", "", 1)
    parts = uri.split("/")
    if len(parts) >= 3:
        handle = parts[0]
        post_id = parts[2]
        return handle, post_id
    return None, None

def build_at_uri(handle: str, post_id: str):
    """
    e.g. 'at://handle/app.bsky.feed.post/post_id'
    """
    return f"at://{handle}/app.bsky.feed.post/{post_id}"

def fetch_post_with_backoff(client, at_uri, max_retries=5):
    """
    A simple backoff strategy to avoid immediate repeated 429 rate-limit errors.
    """
    sleep_seconds = 10
    for attempt in range(1, max_retries + 1):
        try:
            response = client.get_post_thread(uri=at_uri)
            return response.thread.post.record.text
        except RequestException as e:
            # Check if rate-limited
            if "RateLimitExceeded" in str(e):
                print(f"[Attempt {attempt}] Rate limited. Sleeping {sleep_seconds}s ...")
                time.sleep(sleep_seconds)
                sleep_seconds *= 2
            else:
                # Some other error—re-raise
                raise e

    raise Exception(f"Failed to fetch {at_uri} after {max_retries} attempts.")

def fetch_post_content_from_bluesky(uri: str, client: Client) -> str:
    """
    Uses the atproto client to fetch the post text from Bluesky.
    """
    handle, post_id = parse_at_uri(uri)
    if not handle or not post_id:
        return "Failed to parse URI"

    at_uri = build_at_uri(handle, post_id)

    try:
        post_text = fetch_post_with_backoff(client, at_uri)
        return post_text
    except Exception as e:
        print(f"Error fetching post for {uri}: {str(e)}")
        return f"Error: {str(e)}"

def update_new_posts():
    """
    1) Reads from feed_database2.db for all posts
    2) For each post, checks if we already have that CID in content_database.db
    3) If not, fetches real text from Bluesky and stores it (along with URI, username).
    """
    # Initialize Bluesky client once
    client = Client()
    client.login(BSKY_HANDLE, BSKY_APP_PASSWORD)

    p_count = 1
    with db.connection_context():
        posts = Post.select()
        with new_db.connection_context():
            for post in posts:
                # Check if we already have it in PostContent
                exists = PostContent.select().where(PostContent.cid == post.cid).first()
                if exists:
                    continue

                # Parse handle from the at:// URI
                handle, _ = parse_at_uri(post.uri)

                # Fetch real text from Bluesky
                content_text = fetch_post_content_from_bluesky(post.uri, client)

                # Create a new record with all the fields we want
                PostContent.create(
                    cid=post.cid,
                    uri=post.uri,
                    username=handle,
                    content_text=content_text
                )
                print(f"Added new post #{p_count} content for CID: {post.cid}")
                p_count += 1