import requests
import json
from datetime import datetime, timedelta
from newspaper import Article

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk.tokenize import sent_tokenize, word_tokenize
import re

import time

import firebase_admin
from firebase_admin import credentials, firestore
#from firebase_admin import db

class NewsTools:
    def __init__(self):
        nltk.download('stopwords')
        nltk.download('wordnet')
        nltk.download('punkt')
        self.stopW = stopwords.words('english')


    def get_article(self, url):
        # https://towardsdatascience.com/text-cleaning-methods-for-natural-language-processing-f2fc1796e8c7
        article = Article(url)
        try:
            article.download()
        except:
            time.sleep(60)
            article.download()
        article.parse()
        return article.title + ". " + article.text

    def clean_text(self, text):
        text = text.replace('/', ' ')
        tokens = word_tokenize(text)  # tokenize word
        tokens = [word for word in tokens if word.isalpha()]  # remove punct
        tokens = [w.lower() for w in tokens]  # make everthing lowercase to remove stopwords
        stop_words = set(stopwords.words('english'))  # remove stopwords
        tokens = [w for w in tokens if not w in stop_words]
        stemmer = PorterStemmer()  # stem
        for index in range(len(tokens)):
            tokens[index] = stemmer.stem(tokens[index])
        return tokens

    def get_text_ticker(self, url):
        article_text = self.get_article(url)
        match = re.match(".*(NYSE|NASDAQ|Nyse|Nasdaq):\\s*((?:\\w|\\d){1,5}).*", article_text, flags=re.DOTALL)
        if match is None:
            return None
        listOfWords = self.clean_text(article_text)
        return {'words': listOfWords,
                'ticker': match.group(2)}


class FB2:
    def __init__(self):
        self.cred = credentials.Certificate('sentimentdatabase-firebase-adminsdk-u3ll8-f84d6f3c27.json')
        self.default_app = firebase_admin.initialize_app(self.cred)
        self.db = firestore.client(self.default_app)
        self.art1_ref = self.db.collection(u'Article')
        self.art2_ref = self.db.collection(u'Article2')
        self.art3_ref = self.db.collection(u'AfterMarket')


    def getHash(self, h):
        doc = self.art1_ref.document(h).get()
        if doc.exists:
            return doc.to_dict()
        else:
            return None

    def getAfter(self, dt):
        after = []
        stream = self.art1_ref.where(u'time', u'>=', dt.timestamp()).stream()
        for i in stream:
            after.append((i.id, i.to_dict()))
        return after

    def getBetween(self, start, end):
        after = []
        stream = self.art1_ref.where(u'time', u'>=', start.timestamp()).where(u'time', u'<=', end.timestamp()).stream()
        for i in stream:
            after.append((i.id, i.to_dict()))
        return after

    def fireSaveArticle2(self, key, value):
        self.art2_ref.document(key).set(value)
        if self.art2_ref.document(key).get().exists:
            return True
        return False

    def fireSaveAfterMarket(self, key, value):
        self.art3_ref.document(key).set(value)
        if self.art3_ref.document(key).get().exists:
            return True
        return False

