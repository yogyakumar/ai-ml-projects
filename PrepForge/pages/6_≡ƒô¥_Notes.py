import streamlit as st

from database import db

st.set_page_config(page_title="Notes", page_icon="📝", layout="wide")

if "user" not in st.session_state:
    st.warning("Please log in from the main Dashboard page first.")
    st.stop()

user = st.session_state["user"]
st.title("📝 Notes")
st.caption("Markdown + code notes. Add tags to organize by topic (e.g. `dsa, graphs, revision`).")

with st.expander("➕ New note", expanded=True):
    with st.form("note_form", clear_on_submit=True):
        title = st.text_input("Title *")
        content = st.text_area(
            "Content (Markdown supported — use ``` for code blocks)", height=200
        )
        tags = st.text_input("Tags (comma separated)")
        submitted = st.form_submit_button("Save note")
    if submitted:
        if not title.strip():
            st.error("Title is required.")
        else:
            db.add_note(user["id"], title, content, tags)
            st.success("Note saved.")
            st.rerun()

st.divider()

col1, col2 = st.columns([2, 1])
search = col1.text_input("🔍 Search notes")
all_tags = db.all_note_tags(user["id"])
tag_filter = col2.selectbox("Filter by tag", ["All"] + all_tags)

notes = db.get_notes(user["id"], search=search, tag="" if tag_filter == "All" else tag_filter)

st.subheader(f"{len(notes)} note(s)")
for n in notes:
    with st.expander(f"{n['title']}  —  _{n['tags'] or 'no tags'}_"):
        st.markdown(n["content"] or "*empty*")
        st.caption(f"Created: {n['created_at']}")
        if st.button("🗑️ Delete", key=f"del-note-{n['id']}"):
            db.delete_note(n["id"])
            st.rerun()

st.info(
    "Note: image/PDF *file* uploads aren't wired up yet in this version — "
    "for now, paste image/PDF links inside the note content. That's a good next add-on."
)
