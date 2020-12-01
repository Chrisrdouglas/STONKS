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

def quote(ticker, time):
    # get the data from AlphaVantage
    alphaParamaters = {'function': 'TIME_SERIES_INTRADAY',
         'symbol': ticker,
         'interval': '1min',
         'outputsize': 'full',
         'apikey': '6JLE66WZ12ID4D5L'}
    query = requests.get("https://www.alphavantage.co/query", alphaParamaters)
    responses = json.loads(query.text)

    # convert the times into something i can work with
    times = []
    for response in responses['Time Series (1min)']:
        date = datetime.strptime(response, "%Y-%m-%d %H:%M:%S")
        epoch = date.timestamp() - 10800 # 10800 is the time offset between the east and west coast in seconds
        times.append((epoch, response))

    # use the given time to find the closest element in the time series
    closestTime = times[min(range(len(times)), key=lambda x: abs(times[x][0]-time))]
    closest = closestTime[1]
    closestEpoch = closestTime[0]
    averagePrice = (float(responses['Time Series (1min)'][closest]['2. high']) + float(
        responses['Time Series (1min)'][closest]['3. low'])) / 2.0 # average price for that minute

    # calculate the average high price following the price at the time the news was released
    inDayHigh = 0.0
    for epoch in times:
        if epoch[0] > closestEpoch:
            inDayHigh = max(inDayHigh, float(responses['Time Series (1min)'][epoch[1]]['2. high']))
            highTime = epoch[0]
    if inDayHigh == 0.0:
        inDayHigh = averagePrice
        highTime = closestEpoch

    return (averagePrice, inDayHigh, highTime)


tNow = datetime.now()

marketOpenDelta = timedelta(hours=1)
marketCloseDelta = timedelta(hours=13)
tDelta = timedelta(days=1, hours=tNow.hour, minutes=tNow.minute, seconds=tNow.second, microseconds=tNow.microsecond)
midnight = tNow - tDelta

marketOpen = midnight + marketOpenDelta
marketClose = midnight + marketCloseDelta


ns = NewsTools()
fb2 = FB2()

articleHashes = fb2.getBetween(midnight, marketClose)
for i in articleHashes:
    h = i[0]
    dic = i[1]
    nlp = ns.get_text_ticker(dic['link'])
    if nlp is None:
        continue

    price, high, highTime = quote(nlp['ticker'], dic['time'])

    results = {'price': price,
               'ticker': nlp['ticker'],
               'words': nlp['words'],
               # 'closing': close,
               'high': high,
               'highTime': highTime}
    fb2.fireSaveArticle2(h, results)
    time.sleep(15)
