import streamlit as st
import os
from book_scraper import BookScraper

# # Configuration
BASEX_CONFIG = {
    "host": "localhost",
    "port": 1984,
}
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

def main():
    scraper = None

    try:
        st.set_page_config(page_title="Book Scraper with BaseX", layout="wide")
        st.title("📚 Book Scraper with BaseX Integration")
        
        scraper = BookScraper()
        
        with st.sidebar:
            st.header("Configuration")
            book_limit = st.slider("Number of books to scrape:", 1, 200, 10)
            
            st.info("BaseX Connection Settings")
            st.code(f"Host: {BASEX_CONFIG['host']}\nPort: {BASEX_CONFIG['port']}")
            
            st.subheader("Natural Language Query")
            nlp_query = st.text_input("Ask about books in natural language:")
            
            check_nlp_and_xquery(scraper, nlp_query)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("🔄 Scrape and Store Books") or ("has_data" in st.session_state and st.session_state['has_data']):
                check_for_data_and_visualize(scraper, book_limit)
        with col2:
            if ("has_data" in st.session_state and st.session_state['has_data']) or st.button("📊 Run Sample Queries"):
                display_sample_queries(scraper)
    finally:
        if scraper and scraper.basex.is_basex_alive():
            scraper.basex.close()

def check_nlp_and_xquery(scraper, nlp_query):
    """
    This function enables:

    Conversion of a natural language query to XQuery using a model-backed method.
    Allowing users to edit and execute the generated XQuery.
    Caching and displaying results interactively.
    """
    if st.button("Convert") or ("xquery" in st.session_state and st.session_state['xquery']):
        if nlp_query:
            if ("nlp_query" in st.session_state and st.session_state['nlp_query'] == nlp_query):
                xquery = st.session_state['xquery']
            else:
                with st.spinner("Converting to XQuery..."):
                    xquery = scraper.nlp_to_xquery(nlp_query)
                st.session_state['nlp_query'] = nlp_query
            if xquery:
                st.subheader("Generated XQuery:")
                xquery = st.text_area("Editable XQuery", xquery)

                st.session_state['xquery'] = xquery
    
                if st.button("Run edited XQuery"):
                    with st.spinner("Running query..."):
                        results = scraper.query_books(xquery)
                        st.session_state['nlp_result'] = results
                elif ("nlp_result" in st.session_state and st.session_state['nlp_result']):
                    results = st.session_state['nlp_result']
                else:
                    with st.spinner("Running query..."):
                        results = scraper.query_books(xquery)
                        st.session_state['nlp_result'] = results
                st.subheader("Results:")
                if results:
                    for item in results:
                        st.write(f"• {str(item)}")
                else:
                    st.info("No results found")
        else:
            st.warning("Please enter a query")

def display_sample_queries(scraper):
    """
    Displays a set of predefined XQuery examples
    """
    queries = {
        "Books under £50": """
            for $b in /books/item
            where number(substring-after($b/price, '£')) < 50
            return data($b/title/text())
        """,
        "Books by Category": """
            for $c in distinct-values(/books/item/category)
            return concat($c, ': ', count(/books/item[category=$c]))
        """,
        "Top Rated Books": """
            for $b in /books/item[rating='Five']
            return concat($b/title/text(), ' (', $b/rating/text(), ' stars)')
        """
    }
    for name, query in queries.items():
        st.subheader(name)
        results = scraper.query_books(query)
        for item in results:
            st.write(f"• {str(item)}")

def check_for_data_and_visualize(scraper, book_limit):
    """This function checks if book data needs to be scraped and stored, based on the book_limit or session state,
    and then visualizes the category-rating distribution.
    """
    if not ("has_data" in st.session_state or "book_limit" in st.session_state) or book_limit != st.session_state['book_limit']:
        st.session_state['book_limit'] = book_limit
        books_data = scraper.scrape_books(book_limit)
        if scraper.store_in_basex(books_data):
            st.success("✅ Data stored in BaseX successfully!")
            st.session_state['has_data'] = True
            scraper.visualize_category_rating_from_basex()

        else:
            st.error("❌ Failed to store in BaseX")
    else:
        scraper.visualize_category_rating_from_basex()

if __name__ == "__main__":
    main()