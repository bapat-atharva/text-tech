import streamlit as st
import json
import requests
from bs4 import BeautifulSoup
from dicttoxml import dicttoxml
from xml.dom.minidom import parseString
from lxml import etree
from BaseXClient import BaseXClient
import time

# Configuration
BASEX_CONFIG = {
    "host": "localhost",
    "port": 1984,
    "user": "admin",
    "password": "admin"
}

class BaseXConnection:
    def __init__(self):
        self.client = None

    def connect(self):
        try:
            self.client = BaseXClient.Session(
                BASEX_CONFIG["host"],
                BASEX_CONFIG["port"],
                BASEX_CONFIG["user"],
                BASEX_CONFIG["password"]
            )
            return True
        except Exception as e:
            st.error(f"BaseX Connection Error: {e}")
            return False

    def close(self):
        if self.client:
            self.client.close()

class BookScraper:
    def __init__(self):
        self.base_url = "https://books.toscrape.com/"
        self.basex = BaseXConnection()

    def scrape_books(self, limit=200):
        books_data = []
        page = 1
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while len(books_data) < limit:
            try:
                status_text.text(f"Scraping page {page}...")
                url = f"{self.base_url}catalogue/page-{page}.html" if page > 1 else self.base_url
                
                response = requests.get(url)
                if response.status_code != 200:
                    break
                    
                soup = BeautifulSoup(response.content, 'html.parser')
                books = soup.select('article.product_pod')
                
                if not books:
                    break
                    
                for book in books:
                    if len(books_data) >= limit:
                        break
                        
                    product_url = self.base_url + "catalogue/" + book.select_one('h3 a')['href'].replace('../', '')
                    book_data = {
                        "title": book.h3.a['title'],
                        "price": book.select_one('p.price_color').text.strip(),
                        "rating": book.select_one('p.star-rating')['class'][1],
                        "availability": book.select_one('p.availability').text.strip(),
                        "image_url": self.base_url + book.select_one('img')['src'].replace('../', ''),
                        "product_url": product_url,
                        "category": self.get_category(product_url)
                    }
                    books_data.append(book_data)
                    progress_bar.progress(min(len(books_data) / limit, 1.0))
                
                page += 1
                time.sleep(0.5)
                
            except Exception as e:
                st.error(f"Error on page {page}: {e}")
                break
                
        status_text.text(f"Completed! Scraped {len(books_data)} books")
        return books_data

    def get_category(self, url):
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            breadcrumb = soup.find('ul', class_='breadcrumb')
            if breadcrumb:
                links = breadcrumb.find_all('a')
                if len(links) >= 3:
                    return links[2].text.strip()
        except:
            pass
        return 'Unknown'

    def store_in_basex(self, books_data):
        if not self.basex.connect():
            return False

        try:
            # Convert to XML
            xml_data = dicttoxml(books_data, custom_root='books', attr_type=False)
            xml_string = parseString(xml_data).toprettyxml()

            # Create database
            self.basex.client.execute("DROP DB IF EXISTS BookCatalog")
            self.basex.client.create("BookCatalog", xml_string)
            return True

        except Exception as e:
            st.error(f"BaseX Store Error: {e}")
            return False
        finally:
            self.basex.close()

    def query_books(self, query_string):
        if not self.basex.connect():
            return []

        try:
            result = self.basex.client.execute(f"XQUERY {query_string}")
            return result.split('\n') if result else []
        except Exception as e:
            st.error(f"Query Error: {e}")
            return []
        finally:
            self.basex.close()

def main():
    st.set_page_config(page_title="Book Scraper with BaseX", layout="wide")
    st.title("📚 Book Scraper with BaseX Integration")

    scraper = BookScraper()

    with st.sidebar:
        st.header("Configuration")
        book_limit = st.slider("Number of books to scrape:", 1, 200, 50)
        st.info("BaseX Connection Settings")
        st.code(f"Host: {BASEX_CONFIG['host']}\nPort: {BASEX_CONFIG['port']}")

    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("🔄 Scrape and Store Books"):
            books_data = scraper.scrape_books(book_limit)
            if books_data:
                if scraper.store_in_basex(books_data):
                    st.success("✅ Data stored in BaseX successfully!")
                    st.session_state['has_data'] = True
                else:
                    st.error("❌ Failed to store in BaseX")

    with col2:
        if st.button("📊 Run Sample Queries") and st.session_state.get('has_data'):
            queries = {
                "Books under £15": """
                    for $b in /books/book
                    where number(translate($b/price, '£', '')) < 15
                    return concat($b/title/text(), ' (', $b/price/text(), ')')
                """,
                "Books by Category": """
                    for $c in distinct-values(/books/book/category)
                    return concat($c, ': ', count(/books/book[category=$c]))
                """,
                "Top Rated Books": """
                    for $b in /books/book[rating='Five']
                    return concat($b/title/text(), ' (', $b/rating/text(), ' stars)')
                """
            }

            for name, query in queries.items():
                st.subheader(name)
                results = scraper.query_books(query)
                for result in results:
                    if result.strip():
                        st.write(f"• {result}")

if __name__ == "__main__":
    main()