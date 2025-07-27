**Requirements (tested on):**

1. Java v11
2. BaseX v11.9
3. Python v3.12

**Install libraries:**

pip install beautifulsoup4 BaseXClient lxml streamlit huggingface_hub plotly dicttoxml

**Steps:**

1. Set basex password: basexhttp -c "PASSWORD admin" or update your password under basex_conn.py
2. Run ""basexserver"" on cmd to run baseX database
3. Run streamlit 'python -m streamlit run .\main.py'
4. A free tier token is already present under book_scraper.py to make use of LLM
