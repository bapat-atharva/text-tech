# 📚 Web2XML: Structured Book Metadata Extraction and Query System


**Web2XML** is a full-stack text technology pipeline that scrapes book data from the web, converts it into structured XML, validates it against a RelaxNG schema, stores it in the XBase XML-native database, and enables querying via XQuery with an optional natural language interface powered by a Large Language Model (LLM).


---


## 🚀 Features


- Scrapes live book data from [books.toscrape.com](https://books.toscrape.com)
- Converts scraped data into well-formed XML using `dicttoxml`
- Validates XML with a custom **RelaxNG** schema
- Stores data in **XBase** (BaseX) XML database
- Enables querying via **XPath** / **XQuery**
- Natural language to XQuery conversion using **few-shot LLM prompts**
- Sample query execution and results display in **Streamlit**
- Interactive visualizations (e.g., books per category)


---


## 🛠️ Technologies Used


- **Python** (BeautifulSoup, Requests, lxml, Streamlit)
- **XML + RelaxNG**
- **BaseX** (XBase XML-native DB)
- **XQuery / XPath**
- **XSLT (for future styling)**
- **Transformers** (Hugging Face LLM for query generation)


---


## 📁 Project Structure


```
.
├── app.py                # Streamlit UI and control flow
├── books_schema.rng     # RelaxNG schema definition
├── BaseXClient.py       # BaseX Python client
├── utils/               # Helper modules (scraping, validation)
└── README.md            # This file
```


---


## ⚙️ How to Run


1. **Install Dependencies**
  ```bash
  pip install -r requirements.txt
  ```


2. **Start BaseX Server**
  Ensure [BaseX](https://basex.org/download/) is running locally on port `1984`.


3. **Launch the Streamlit App**
  ```bash
  streamlit run app.py
  ```


4. **Use the Sidebar**
  - Select number of books to scrape.
  - Optionally enter a natural language query (e.g., "books under £15").


---


## 💡 Example Natural Language Queries


- `Books under £20`
- `Top rated books`
- `Count of books in each category`


The system will attempt to convert these into XQuery via the LLM and run them on the stored XML data.


---


## 🧠 Known Limitations


- LLM prompt context is restricted due to token limitations on free API tier.
- Scope is limited to predefined XML structure and query types.
- Query sandbox is provided for manual correction of generated XQuery.


---


## 📊 Sample Queries Provided


- Books under a certain price
- Count of books per category
- Books with highest ratings


---


## 📜 License


This project is for academic use as part of the **Text Technology course at Universität Stuttgart**.


---


## 👥 Authors


- Amogh Mathad 
- A Yogi Athish 
- Atharva Bapat


