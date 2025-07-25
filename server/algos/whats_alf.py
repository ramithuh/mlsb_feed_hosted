from datetime import datetime
from typing import Optional

from server import config
from server.database import Post

uri = config.WHATS_ALF_URI
CURSOR_EOF = 'eof'

# Define your sticky post uri
sitcky_uri1 = "at://did:plc:a33wx75tk3vfmbqb6brpbxo4/app.bsky.feed.post/3leve7zx2zk2r"
sticky_uri2 = "at://did:plc:a33wx75tk3vfmbqb6brpbxo4/app.bsky.feed.post/3lulf4zaacc2o"

def handler(cursor: Optional[str], limit: int) -> dict:
    posts = Post.select().order_by(Post.cid.desc()).order_by(Post.indexed_at.desc()).limit(limit)

    if cursor:
        if cursor == CURSOR_EOF:
            return {
                'cursor': CURSOR_EOF,
                'feed': []
            }
        cursor_parts = cursor.split('::')
        if len(cursor_parts) != 2:
            raise ValueError('Malformed cursor')

        indexed_at, cid = cursor_parts
        indexed_at = datetime.fromtimestamp(int(indexed_at) / 1000)
        posts = posts.where(((Post.indexed_at == indexed_at) & (Post.cid < cid)) | (Post.indexed_at < indexed_at))

    feed = [{'post': sitcky_uri1}] +[{'post': sticky_uri2}] + [{'post': post.uri} for post in posts]

    cursor = CURSOR_EOF
    last_post = posts[-1] if posts else None
    if last_post:
        cursor = f'{int(last_post.indexed_at.timestamp() * 1000)}::{last_post.cid}'

    return {
        'cursor': cursor,
        'feed': feed
    }
