import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
from dicttoxml import dicttoxml
from xml.dom.minidom import parseString
from lxml import etree
from BaseXClient import BaseXClient
import time
from transformers import pipeline

# Configuration
BASEX_CONFIG = {
    "host": "localhost",
    "port": 1984,
    "user": "admin",
    "password": "admin"
}
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
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

    def validate_xml(self, xml_file: str, schema_file: str = "./books_schema.rng") -> bool:
        """
        Validate XML against RelaxNG schema
        Returns True if valid, False otherwise
        """
        try:
            if not os.path.exists(schema_file):
                raise FileNotFoundError(f"Schema file not found: {schema_file}")
                
            # Parse the XML file and schema
            xml_doc = etree.fromstring(xml_file)
            # with open("aa.xml", "w") as f:
            #     f.write(xml_file)

            relaxng_doc = etree.RelaxNG(etree.parse(schema_file))
                
            # Validate and return result
            is_valid = relaxng_doc.validate(xml_doc)
            
            if is_valid:
                st.success("✅ XML document is valid against the schema")
            else:
                st.success("❌ XML validation failed!")
                for error in relaxng_doc.error_log:
                    print(f"Line {error.line}: {error.message}")
                
            return is_valid
            
        except Exception as e:
            print(f"Validation error: {str(e)}")
            return False

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
                        
                    product_url = self.base_url + "catalogue/" + book.select_one('h3 a')['href'].replace('../', '').replace("catalogue", "")
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

            self.validate_xml(xml_string)

            # Create database
            self.basex.client.execute("drop db BookCatalog")

            self.basex.client.execute("create db BookCatalog " + xml_string)


            return True

        except Exception as e:
            st.error(f"BaseX Store Error: {e}")
            return False
        finally:
            # self.basex.close()
            pass

    def query_books(self, query_string):
        if not self.basex.connect():
            return []
        
        self.basex.client.execute("open BookCatalog")

        try:
            # print(query_string)
            result = self.basex.client.query(query_string)
            return result
        except Exception as e:
            st.error(f"Query Error: {e}")
            return []
        finally:
            # self.basex.close()
            pass
    # def nlp_to_xquery(self, nlp_query):
    #     """Convert natural language query to XQuery using Hugging Face"""
    #     if not HF_API_TOKEN:
    #         st.error("Hugging Face API token is not set. Please set HF_API_TOKEN environment variable.")
    #         return None

    #     try:
    #         client = InferenceClient(token=HF_API_TOKEN)
            
    #         prompt = f"""
    #         Convert the following natural language query about books into valid XQuery 3.1:
    #         The XML structure has books at path '/books/item' with these child elements:
    #         - title
    #         - price (format: £XX.XX)
    #         - rating (values: One, Two, Three, Four, Five)
    #         - availability
    #         - image_url
    #         - product_url
    #         - category
            
    #         Query: "{nlp_query}"
            
    #         Return ONLY the XQuery code without any additional explanation or formatting.
    #         Make sure the query:
    #         1. Starts with 'xquery version "3.1";'
    #         2. Uses proper string manipulation for price comparisons
    #         3. Handles categories as strings
    #         4. Returns meaningful results with element names
            
    #         Example response for 'books under £15':
    #         xquery version "3.1";
    #         for $book in /books/item
    #         where number(substring($book/price, 2)) < 15
    #         return $book/title
    #         """
            
    #         response = client.text_generation(
    #             prompt=prompt,
    #             model="HuggingFaceH4/starchat-beta",
    #             max_new_tokens=256,
    #             temperature=0.1,
    #             stop_sequences=["<|end|>"]
    #         )
            
    #         # Clean up the response
    #         xquery = response.strip()
    #         if "```xquery" in xquery:
    #             xquery = xquery.split("```xquery")[1].split("```")[0].strip()
    #         elif "```" in xquery:
    #             xquery = xquery.split("```")[1].split("```")[0].strip()
                
    #         return xquery
            
    #     except Exception as e:
    #         st.error(f"LLM Conversion Error: {e}")
    #         return None

    def nlp_to_xquery(self, nlp_query):
        if not HF_API_TOKEN:
            st.error("Hugging Face API token is not set. Please set HF_API_TOKEN environment variable.")
            return None

        try:
            # Load the model pipeline
            generator = pipeline(
                "text-generation",
                model="HuggingFaceH4/starchat-beta",
                token="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"
            )

            prompt = f"""
            Convert the following natural language query about books into valid XQuery 3.1:
            The XML structure has books at path '/books/item' with these child elements:
            - title
            - price (format: £XX.XX)
            - rating (values: One, Two, Three, Four, Five)
            - availability
            - image_url
            - product_url
            - category

            Query: "{nlp_query}"

            Return ONLY the XQuery code without any additional explanation or formatting.
            Make sure the query:
            1. Starts with 'xquery version "3.1";'
            2. Uses proper string manipulation for price comparisons
            3. Handles categories as strings
            4. Returns meaningful results with element names

            Example response for 'books under £15':
            xquery version "3.1";
            for $book in /books/item
            where number(substring($book/price, 2)) < 15
            return $book/title
            """

            # Generate the response
            results = generator(prompt, max_new_tokens=256, temperature=0.1)
            xquery = results[0]['generated_text'].strip()

            # Clean up the response
            if "```xquery" in xquery:
                xquery = xquery.split("```xquery")[1].split("```")[0].strip()
            elif "```" in xquery:
                xquery = xquery.split("```")[1].split("```")[0].strip()

            return xquery

        except Exception as e:
            st.error(f"LLM Conversion Error: {e}")
            return None

    def visualize_category_rating_from_basex(self, host='localhost', port=1984, username='admin', password='admin', db_name='books_db'):
        """
        Connects to BaseX, runs an XQuery to extract <category, rating> pairs,
        aggregates the data, and visualizes it as a grouped bar chart using Plotly.
        """

        if not self.basex.connect():
            return []
        
        self.basex.client.execute("open BookCatalog")

        # # --- 1. Connect to BaseX ---
        # try:
        #     session = Session(host, port, username, password)
        #     session.execute(f"open {db_name}")
        # except Exception as e:
        #     print(f"❌ Connection failed: {e}")
        #     return

        # --- 2. XQuery to extract category and rating ---
        xquery = """
        for $b in /books/item
        return concat($b/category, ",", $b/rating)
        """

        try:
            raw_result = self.basex.client.query(xquery).execute()
            lines = raw_result.strip().split('\n')
        except Exception as e:
            print(f"❌ XQuery failed: {e}")
            return

        # --- 3. Convert to DataFrame ---
        data = [line.strip().split(',') for line in lines if ',' in line]
        df = pd.DataFrame(data, columns=['category', 'rating'])

        # --- 4. Optional: Order ratings ---
        rating_order = ['One', 'Two', 'Three', 'Four', 'Five']
        df['rating'] = pd.Categorical(df['rating'], categories=rating_order, ordered=True)

        # --- 5. Group and count ---
        grouped = df.groupby(['category', 'rating']).size().reset_index(name='count')

        # --- 6. Visualize using Plotly ---
        fig = px.bar(
            grouped,
            x='category',
            y='count',
            color='rating',
            barmode='group',
            title='Books per Category and Rating',
            labels={'count': 'Number of Books'}
        )

        st.plotly_chart(fig, use_container_width=True)



import pandas as pd
import plotly.express as px

def main():
    try:
        st.set_page_config(page_title="Book Scraper with BaseX", layout="wide")
        st.title("📚 Book Scraper with BaseX Integration")

        scraper = BookScraper()

        with st.sidebar:
            st.header("Configuration")
            book_limit = st.slider("Number of books to scrape:", 1, 200, 10)
            st.info("BaseX Connection Settings")
            st.code(f"Host: {BASEX_CONFIG['host']}\nPort: {BASEX_CONFIG['port']}")

            # NLP to XQuery section
            st.subheader("Natural Language Query")
            nlp_query = st.text_input("Ask about books in natural language:")
            if st.button("Convert & Run"):
                if nlp_query:
                    with st.spinner("Converting to XQuery..."):
                        xquery = scraper.nlp_to_xquery(nlp_query)
                        
                    if xquery:
                        st.subheader("Generated XQuery:")
                        st.code(xquery, language="xquery")
                        
                        with st.spinner("Running query..."):
                            results = scraper.query_books(xquery)
                            
                        st.subheader("Results:")
                        if results:
                            for item in results:
                                st.write(f"- {item}")
                        else:
                            st.info("No results found")
                else:
                    st.warning("Please enter a query")
        col1, col2 = st.columns([2, 1])

        with col1:
            if st.button("🔄 Scrape and Store Books"):
                books_data = scraper.scrape_books(book_limit)
                if books_data:
                    if scraper.store_in_basex(books_data):
                        st.success("✅ Data stored in BaseX successfully!")
                        st.session_state['has_data'] = True
                        scraper.visualize_category_rating_from_basex()
                    else:
                        st.error("❌ Failed to store in BaseX")

        with col2:
            if st.button("📊 Run Sample Queries"):# and st.session_state.get('has_data'):
                queries = {
                    "Books under £15": """
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
                    for typecode, item in results.iter():
                        # print("typecode=%d" % typecode)
                        print("item=%s" % str(item))
                        st.write(f"• {str(item)}")
    finally:
        scraper.basex.close()
if __name__ == "__main__":
    main()
