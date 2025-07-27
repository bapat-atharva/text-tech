import requests
from bs4 import BeautifulSoup
from dicttoxml import dicttoxml
from xml.dom.minidom import parseString
from lxml import etree
import time
import pandas as pd
import plotly.express as px
import streamlit as st
import os
from basex_conn import BaseXConnection
from huggingface_hub import InferenceClient

HF_API_TOKEN = "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"
class BookScraper:
    def __init__(self):
        self.base_url = "https://books.toscrape.com/"
        self.basex = BaseXConnection()


    def validate_xml(self, xml_file: str, schema_file: str = "./books_schema.rng") -> bool:
        """
        This function validates an XML string against a RelaxNG schema (default: books_schema.rng)
        Returns True if the XML is valid, or False otherwise.
        """
        try:
            if not os.path.exists(schema_file):
                raise FileNotFoundError(f"Schema file not found: {schema_file}")
            xml_doc = etree.fromstring(xml_file)
            relaxng_doc = etree.RelaxNG(etree.parse(schema_file))
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
        """
        This method scrapes up to limit book listings from the Books to Scrape website
        Returns a list of structured book data dictionaries.
        """
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
                        "category": self.get_category(product_url),
                    }

                    books_data.append(book_data)
                    progress_bar.progress(min(len(books_data) / limit, 1.0))
                page += 1
                time.sleep(0.5) # avoid overwheling server
            except Exception as e:
                st.error(f"Error on page {page}: {e}")
                break
        status_text.text(f"Completed! Scraped {len(books_data)} books")

        return books_data

    def get_category(self, url):
        """
        This method retrieves the category name of a book from its individual product page on the "Books to Scrape" website.
        """
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
        """
        This method takes structured book data (books_data), serializes it into XML, validates it, 
        saves it to a file, and stores it in a BaseX XML-native database named BookCatalog.
        """
        if not self.basex.connect():
            st.error(f"BaseX Connection Error")
            return False
        try:
            xml_data = dicttoxml(books_data, custom_root='books', attr_type=False)
            xml_string = parseString(xml_data).toprettyxml()
            self.validate_xml(xml_string)
            # Create XML tree and save to file
            # root = etree.fromstring(xml_string.encode('utf-8'))
            # tree = etree.ElementTree(root)
            # tree.write(
            #     "xml_file.xml", 
            #     pretty_print=True, 
            #     encoding='utf-8', 
            #     xml_declaration=True
            # )
            self.basex.client.execute("drop db BookCatalog")
            self.basex.client.execute("create db BookCatalog " + xml_string)
            return True
        except Exception as e:
            st.error(f"BaseX Store Error: {e}")
            return False
        finally:
            self.basex.close()

    def query_books(self, query_string):
        """
        This method executes an XQuery string against a BaseX XML database and returns the results as a list of non-empty strings.
        """
        if not self.basex.connect_db():
            return []

        try:
            query = self.basex.client.query(query_string)
            result_str = query.execute()

            return [line for line in result_str.strip().split('\n') if line.strip()]
        except Exception as e:
            st.error(f"Query Error: {e}")
            return []
        finally:
            self.basex.close()

    def nlp_to_xquery(self, nlp_query):
        """
        This function translates a natural language question (nlp_query) into an XQuery expression using 
        an LLM Mixtral accessed via Hugging Face's inference API.
        """
        if not HF_API_TOKEN:
            st.error("Hugging Face API token is not set. Please set HF_API_TOKEN environment variable.")
            return None
        try:

            # Few-shot examples
            few_shot = """
            # Sample question and their equivalent xquery
            Q: List all book titles under £15.
            A:for $book in /books/item
            where number(substring($book/price, 2)) < 15
            return $book/title/text()

            Q: Show titles and prices of books in the 'Science Fiction' category.
            A:for $book in /books/item
            where $book/category = "Science Fiction"
            return { $book/title/text() - $book/price/text() }

            Q: List all books with a rating of Five.
            A:for $book in /books/item
            where $book/rating = "Five"
            return $book/title/text()

            Q: Number of books under price of 50 pounds
            A:count(
            for $b in /books/item
            let $price := number(translate($b/price, "£", ""))
            where $price < 50
            return $b
            )

            Q: {user_query}
            A:
            # Return ONLY the XQuery code, with no explanation, markdown, or formatting.
            """.replace("{user_query}", nlp_query)


            client = InferenceClient(model="mistralai/Mixtral-8x7B-Instruct-v0.1", token=HF_API_TOKEN)
            response = client.chat_completion(
                messages=[
                    {"role": "user", "content": few_shot}
                ],
                max_tokens=256,
                temperature=0.1
            )
            xquery = response.choices[0].message.content.strip()

            if "```" in xquery:
                xquery = xquery.split("```")[-1].strip()
            # Remove everything before the first 'for $book' or 'xquery version'
            for starter in ["for $book", "xquery version"]:
                if starter in xquery:
                    xquery = xquery[xquery.index(starter):]
                    break
            return xquery
        except Exception as e:
            st.error(f"LLM Conversion Error: {e}")
            return None

    def visualize_category_rating_from_basex(self):
        """
        Connects to BaseX, runs an XQuery to extract <category, rating> pairs,
        aggregates the data, and visualizes it as a grouped bar chart using Plotly.
        """

        if not self.basex.connect_db():
            raise Exception("Error opening the database")
        xquery = """
        for $b in /books/item
        return concat($b/category, ",", $b/rating, ",", $b/price)
        """
        try:
            raw_result = self.basex.client.query(xquery).execute()
            lines = raw_result.strip().split('\n')
        except Exception as e:
            print(f"❌ XQuery failed: {e}")
            return
        # Only keep lines with exactly one comma
        data = [line.strip().split(',', 2) for line in lines if line.count(',') == 2]
        if not data:
            st.warning("No category-rating data found in BaseX.")
            return
        df = pd.DataFrame(data, columns=['category', 'rating', 'price'])
        
        df['category'] = df['category'].str.strip()
        df['rating'] = df['rating'].str.strip()
        
        df['price'] = pd.to_numeric(df['price'].str.strip().str.replace('£', '', regex=False), errors='coerce')

        rating_order = ['One', 'Two', 'Three', 'Four', 'Five']
        df['rating'] = pd.Categorical(df['rating'], categories=rating_order, ordered=True)
        df['rating'] = df['rating'].cat.codes + 1

        # Group by category and rating, count occurrences
        grouped = df.groupby(['category', 'rating'], as_index=False).size().rename(columns={'size': 'count'})
        # Remove rows with count 0 (if any)
        grouped = grouped[grouped['count'] > 0]
        # Visualize
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

        # --- Step 1: Let user pick chart type ---
        chart_type = st.selectbox("Select Chart Type", ["Bar", "Box", "Violin", "Scatter"], key=0)

        # --- Step 2: Select X and Y axes ---
        available_fields = df.columns.tolist()
        x_axis = st.selectbox("Select X-Axis", options=available_fields, index=0)
        y_axis = st.selectbox("Select Y-Axis", options=available_fields, index=1)  # default: price

        # --- Step 3: Group data if needed ---
        agg_method = st.selectbox("Aggregation (if duplicate x-y values)", ["count", "mean", "sum", "none"])
        if agg_method != "none":
            if agg_method == "count":
                grouped_df = df.groupby(x_axis).size().reset_index(name=y_axis + " " + agg_method)
            else:
                # Optional: validate
                if not pd.api.types.is_numeric_dtype(df[y_axis]):
                    st.error(f"Cannot compute {agg_method} on non-numeric column '{y_axis}'")
                    st.stop()
                grouped_df = df.groupby(x_axis).agg({y_axis: agg_method}).reset_index()
                grouped_df = grouped_df.rename(columns={y_axis: y_axis + " " + agg_method})

            df_to_plot = grouped_df
            y_axis_plot = y_axis + " " + agg_method
        else:
            df_to_plot = df
            y_axis_plot = y_axis


        # Select color column
        color_col = st.selectbox("Select Color Column (optional)", options=[None] + available_fields, index=0)

        # Set color_arg only if it's present in the current df_to_plot
        color_arg = color_col if (color_col and color_col in df_to_plot.columns) else None

        # Optional warning
        if color_col and color_col not in df_to_plot.columns:
            st.warning(f"Column '{color_col}' is not available after aggregation — color will be ignored.")


        # --- Step 4: Generate chart ---
        fig = None
        if chart_type == "Bar":
            fig = px.bar(df_to_plot, x=x_axis, y=y_axis_plot, color=color_arg, barmode='group')
        elif chart_type == "Box":
            fig = px.box(df_to_plot, x=x_axis, y=y_axis_plot, color=x_axis)
        elif chart_type == "Violin":
            fig = px.violin(df_to_plot, x=x_axis, y=y_axis_plot, color=x_axis, box=True, points="all")
        elif chart_type == "Scatter":
            fig = px.scatter(df_to_plot, x=x_axis, y=y_axis_plot, color=color_arg)

        st.plotly_chart(fig, use_container_width=True)
