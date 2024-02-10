
# Name: ai_news_auto_poster.py
# Description: Scrap DuckDuckGo website for AI news and let OpenAI to summary then 
#              auto-post to wordpress blog.
# Author: Roger Deng
# Date: 2024-02-10
# Version: 1.0
# Usage: python ai_news_auto_poster.py
#
# ------------------ SQL START --------------------------
# CREATE TABLE `ai_poster` (
#   `cdate` date NOT NULL,
#   `url` varchar(4096) NOT NULL,
#   `title` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
#   `date` varchar(30) NOT NULL,
#   `body` varchar(4096) NOT NULL,
#   `image` varchar(4096) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
#   `source` varchar(1024) NOT NULL
# ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

# ALTER TABLE `ai_poster`
#   ADD PRIMARY KEY (`title`) USING BTREE;
# COMMIT;
#
# ------------------ SQL END --------------------------

import requests
from phi.assistant import Assistant # pip install phidata
from datetime import datetime
from duckduckgo_search import DDGS
from typing import Optional
import mysql.connector
import time
import os
from dotenv import load_dotenv

now = datetime.now() 
date_string = now.strftime("%Y-%m-%d")

load_dotenv()

MYSQL_HOST = os.getenv('mysql_host')
MYSQL_USER = os.getenv('mysql_user')
MYSQL_PASSWORD = os.getenv('mysql_password')
MYSQL_DATABASE = os.getenv('mysql_database')
MYSQL_TABLE = os.getenv('mysql_table')

WORDPRESS_URL = os.getenv('wordpress_url')
WORDPRESS_USER = os.getenv('wordpress_user')
WORDPRESS_PASSWORD = os.getenv('wordpress_password')

mydb = mysql.connector.connect(
  host=MYSQL_HOST,
  user=MYSQL_USER,
  password=MYSQL_PASSWORD,
  database=MYSQL_DATABASE,
  auth_plugin='mysql_native_password'
)
mycursor = mydb.cursor()

class DuckDuckGoNewsScraper:
    def duckduckgo_news(self, query: str, max_results: Optional[int] = 10) -> str:
        ddgs = DDGS(timeout=30)
        news = ddgs.news(keywords=query, max_results=max_results)
        return news
    
    def save_db(self, news: dict) :
        for r in news :
            sql = "INSERT INTO " + MYSQL_TABLE + " (cdate, title, source, body, url, image, date) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            val = (date_string, r['title'], r['source'], r['body'], r['url'], r['image'], r['date'])
            try:
                mycursor.execute(sql, val)
                mydb.commit()
            except:
                print('Exist news')
        return
    
    def query_db(self) :
        sql = "SELECT * FROM " + MYSQL_TABLE + " WHERE cdate = %s"
        val = (date_string, )
        mycursor.execute(sql , val)
        myresult = mycursor.fetchall()
        return myresult
    
    def htmloutput(self, news: dict) :
        html_content =''
        for r in news :
            html_content += '<ol><p>'
            html_content += '<strong>'+r[2] +'</strong>'
            html_content += '<br>(' + r[6] + ')<br>'
            html_content += r[4] + '<br>'
            html_content += '<a href="' + r[1] + '" target="_blank">Read More</a>'
            if r[5] :
                  html_content += '<br><img src="' + r[5] + '" alt="News Image">'
            html_content += '</p></ol>'
        return html_content

scraper = DuckDuckGoNewsScraper()
query = "artificial intelligence"
news_results = scraper.duckduckgo_news(query, max_results=10)
scraper.save_db(news_results)
db_news_results = scraper.query_db()
html_news_results = scraper.htmloutput(db_news_results)
#print(html_news_results)

description = "You are a professional news summary writer for an AI technology news website. Your role is to read news articles and summarize the key points into concise overviews while maintaining accuracy, objectivity and neutrality. Avoid inserting opinions or analysis. Focus on accurately conveying the main news details and developments in a factual and neutral tone. Write professional summaries that are engaging yet precise, optimizing for clarity, brevity and factual integrity."
prompt = "Please summary all news content with one summary around 400 - 500 words"

summary = Assistant(
    #llm=Ollama(model="mixtral:8x7b", options={"temperature": 0.3}), 
    description=description,
    instructions=[
        html_news_results,
    ],
    debug_mode=True
    ,stream=False)

print(summary)
is_run = True
while(is_run) :
    try:
        summary.run("Please summary all news content with one summary around 400 - 500 words",stream=False)
        is_run = False
    except:
        print("Error Ocurred!")
        time.sleep(5)

url = WORDPRESS_URL
username = WORDPRESS_USER
password = WORDPRESS_PASSWORD

# The post data
data = {
    'title': 'Today\'s latest AI tech news feed ('+date_string+')',
    'content':'<p>'+summary.output +'</p> More information, please check below news source: <br>'+ html_news_results,
    'status': 'publish'  # Use 'draft' to save the post as a draft
}

# Send the HTTP request
response = requests.post(url, auth=(username, password), json=data)

# Check the response
if response.status_code == 201:
    print('Post created successfully')
else:
    print('Failed to create post: ' + response.text)
