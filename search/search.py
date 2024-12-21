# streamlit_app.py

import streamlit as st
from new_database import PostContent, new_db
import streamlit.components.v1 as components

def build_multi_post_embed(posts):
    """
    Takes a list of PostContent records and returns one big HTML string
    containing multiple <blockquote> tags plus a single <script> at the end.
    """
    blockquotes = []
    
    for post in posts:
        # Provide some fallback text (trim to e.g. first 100 chars)
        fallback_text = (post.content_text[:100] + "...") if post.content_text else ""
        
        # Build the blockquote for each post (NO <script> tag here)
        bq = f"""
        <blockquote class="bluesky-embed"
                    data-bluesky-uri="{post.uri}"
                    data-bluesky-cid="{post.cid}">
          <p>{fallback_text}</p>
        </blockquote>
        """
        blockquotes.append(bq)
    
    # Join all blockquotes together
    blockquotes_html = "\n".join(blockquotes)
    
    # Add the script only once at the end
    # This will process all .bluesky-embed elements on the page
    embed_script = """
    <script async src="https://embed.bsky.app/static/embed.js" charset="utf-8"></script>
    """
    
    # Wrap it all in basic HTML
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8"/>
      <title>Multiple Bluesky Embeds</title>
    </head>
    <body>
      {blockquotes_html}
      {embed_script}
    </body>
    </html>
    """
    
    return full_html

def main():
    st.title("MLSB Bluesky Post Search")

    # Button to refresh DB
    if st.button("Refresh Posts"):
        import data_update
        data_update.update_new_posts()
        st.success("Database updated with any new posts!")

    # Search box
    query = st.text_input("Search text:")
    if st.button("Search"):
        with new_db.connection_context():
            # Query matching rows
            results = PostContent.select().where(PostContent.content_text.contains(query))

            # Let user know how many we found
            count = results.count()
            st.write(f"Found {count} result(s).")

            if count > 0:
                # Build one HTML snippet with multiple <blockquote> elements
                multi_html = build_multi_post_embed(results)

                # Display everything in a single Streamlit component
                # Increase height if needed; enable scrolling to avoid clipping
                components.html(multi_html, height=1800, scrolling=True)
            else:
                st.info("No results found.")

if __name__ == "__main__":
    main()
