import streamlit as st
import difflib

st.title("🔍 Python File Comparison (Beyond Compare Style)")

# Upload two Python files
file1 = st.file_uploader("Upload First Python File", type=["py"])
file2 = st.file_uploader("Upload Second Python File", type=["py"])

if file1 and file2:
    # Read and decode both files
    code1 = file1.read().decode("utf-8").splitlines()
    code2 = file2.read().decode("utf-8").splitlines()

    # Show side-by-side code
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📄 File 1")
        st.code("\n".join(code1), language="python")
    with col2:
        st.subheader("📄 File 2")
        st.code("\n".join(code2), language="python")

    # Generate and display diff
    st.subheader("🔧 Differences (Unified Diff)")
    diff = difflib.unified_diff(
        code1,
        code2,
        fromfile=file1.name,
        tofile=file2.name,
        lineterm=''
    )
    st.code("\n".join(diff), language="diff")

    # Optionally show HTML diff
    if st.checkbox("Show Side-by-Side HTML Diff"):
        differ = difflib.HtmlDiff()
        html_diff = differ.make_table(code1, code2, fromdesc="File 1", todesc="File 2", context=True, numlines=5)
        st.components.v1.html(html_diff, height=600, scrolling=True)
