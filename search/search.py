# streamlit_app.py

import streamlit as st
from new_database import PostContent, new_db
import streamlit.components.v1 as components

def build_multi_post_embed(posts):
    """
    Takes a list of PostContent records and returns one big HTML string
    containing multiple <bluesky-post> elements plus the required
    <script> and <link> tags in the <head>.
    """
    # We will store all <bluesky-post> blocks in a list, then join them
    post_blocks = []

    for post in posts:
        # Provide some fallback text (e.g. first 100 chars)
        fallback_text = (post.content_text or "")[:100]
        fallback_text_escaped = fallback_text.replace("<", "&lt;").replace(">", "&gt;")

        # The new library uses <bluesky-post src="at://did:plc:...">
        # Then a fallback <blockquote> inside it.
        post_block = f"""
        <bluesky-post src="{post.uri}">
          <blockquote class="bluesky-post-fallback">
            <p>{fallback_text_escaped}</p>
            <p>— {post.username or "Unknown User"}</p>
          </blockquote>
        </bluesky-post>
        """
        post_blocks.append(post_block)

    # Join all <bluesky-post> elements into one
    posts_html = "\n<br>".join(post_blocks)

    # HTML HEAD: We insert the recommended script+CSS from bluesky-post-embed
    #    - The "type=module" script
    #    - The core.css and optional theme files
    #    - The fallback style
    head_tags = """
    <head>
      <!-- Core web component and styling -->
      <script type="module"
              src="https://cdn.jsdelivr.net/npm/bluesky-post-embed@^1.0.0/+esm">
      </script>
      <link rel="stylesheet"
            href="https://cdn.jsdelivr.net/npm/bluesky-post-embed@^1.0.0/dist/core.min.css">

      <!-- Built-in themes (light/dim); load based on OS or user preference -->
      <link rel="stylesheet"
            href="https://cdn.jsdelivr.net/npm/bluesky-post-embed@^1.0.0/themes/light.min.css"
            media="(prefers-color-scheme: light)">
      <link rel="stylesheet"
            href="https://cdn.jsdelivr.net/npm/bluesky-post-embed@^1.0.0/themes/dim.min.css"
            media="(prefers-color-scheme: dark)">

      <!-- Fallback/placeholder elements if JS script is taking a while to load or failing -->
      <style>
        .bluesky-post-fallback {
          margin: 16px 0;
          border-left: 3px solid var(--divider, #bbb);
          padding: 4px 8px;
          white-space: pre-wrap;
          overflow-wrap: break-word;
        }
        .bluesky-post-fallback p {
          margin: 0 0 8px 0;
        }
      </style>
    </head>
    """

    # Combine everything in one big HTML string
    # We wrap <body> around all the <bluesky-post> elements
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
      {head_tags}
      <body>
        {posts_html}
      </body>
    </html>
    """
    
    return full_html

def main():
    # Some custom styling for your Streamlit page
    st.markdown(
        """
        <style>
            [data-testid="stDecoration"] {
                background-image: linear-gradient(90deg, rgb(0, 102, 204), rgb(102, 255, 255));
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h1 style='color: #1185FE;'>Bluesky MLSB Feed's Post Search</h1>",
        unsafe_allow_html=True,
    )

    st.write(
        "This app allows you to search through Bluesky posts in the "
        f"[MLSB Feed](https://bsky.app/profile/ramith.fyi/feed/MLSB)."
    )

    # If you want a Refresh button, you can uncomment these lines:
    # if st.button("Refresh Posts"):
    #     import data_update
    #     data_update.update_new_posts()
    #     st.success("Database updated with any new posts!")

    # Build a simple search form
    with st.form("search_form"):
        query = st.text_input("Search text:")
        submit_button = st.form_submit_button("Search")

    if submit_button:
        with new_db.connection_context():
            results = PostContent.select().where(PostContent.content_text.contains(query))
            count = results.count()
            st.write(f"Found {count} result(s).")

            if count > 0:
                # Generate a single HTML doc with all <bluesky-post> elements
                multi_html = build_multi_post_embed(results)

                # We'll embed it in Streamlit. We can pick a big height or allow scrolling
                components.html(multi_html, height=1800, scrolling=True)
            else:
                st.info("No results found.")

if __name__ == "__main__":
    main()
