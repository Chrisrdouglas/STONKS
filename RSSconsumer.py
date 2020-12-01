import requests
import xml.etree.ElementTree as ET
import firebase_admin
from firebase_admin import credentials, firestore
import hashlib
from time import sleep, time
from datetime import datetime, timedelta


class RSS:
    def __init__(self):
        self.globalsBioSession = requests.Session()
        self.globalsPharmaSession = requests.Session()
        f = self.globalsBioSession.get(
            'https://www.globenewswire.com/RssFeed/industry/4573-Biotechnology/feedTitle/GlobeNewswire%20-%20Industry%20News%20on%20Biotechnology')
        f2 = self.globalsPharmaSession.get(
            'https://www.globenewswire.com/RssFeed/industry/4577-Pharmaceuticals/feedTitle/GlobeNewswire%20-%20Industry%20News%20on%20Pharmaceuticals')
        self.eTagBio = None
        self.eTagPharma = None
        self.eTagAlpha = None

    def __del__(self):
        self.globalsBioSession.close()
        self.globalsPharmaSession.close()

    def resetSessions(self):
        self.globalsBioSession = requests.Session()
        self.globalsPharmaSession = requests.Session()
        f = self.globalsBioSession.get(
            'https://www.globenewswire.com/RssFeed/industry/4573-Biotechnology/feedTitle/GlobeNewswire%20-%20Industry%20News%20on%20Biotechnology')
        f2 = self.globalsPharmaSession.get(
            'https://www.globenewswire.com/RssFeed/industry/4577-Pharmaceuticals/feedTitle/GlobeNewswire%20-%20Industry%20News%20on%20Pharmaceuticals')

    def seekingAlphaHealth(self):
        r = requests.head("https://seekingalpha.com/news/healthcare/feed")
        if r.headers['Etag'] == self.eTagAlpha:
            return None
        r = requests.get("https://seekingalpha.com/news/healthcare/feed")
        xml = ET.fromstring(r.text)
        self.eTagAlpha = r.headers['etag']
        r.close()
        return self.parse(xml)

    def globalNewsWirePharma(self, lastEtag = None):
        #r = requests.get('https://www.globenewswire.com/RssFeed/industry/4577-Pharmaceuticals/feedTitle/GlobeNewswire%20-%20Industry%20News%20on%20Pharmaceuticals')
        r = self.globalsPharmaSession.get('https://www.globenewswire.com/RssFeed/industry/4577-Pharmaceuticals/feedTitle/GlobeNewswire%20-%20Industry%20News%20on%20Pharmaceuticals')
        if r.status_code != 200:
            print(r)
            return []
        #if r.headers['etag'] == self.eTagPharma:
        #    return None
        xml = ET.fromstring(r.text)
        #self.eTagPharma = r.headers['etag']
        return self.parseGlobe(xml)

    def globalNewsWireBio(self, lastEtag = None):
        #r = requests.get('https://www.globenewswire.com/RssFeed/industry/4573-Biotechnology/feedTitle/GlobeNewswire%20-%20Industry%20News%20on%20Biotechnology')
        r = self.globalsBioSession.get('https://www.globenewswire.com/RssFeed/industry/4573-Biotechnology/feedTitle/GlobeNewswire%20-%20Industry%20News%20on%20Biotechnology')
        #if r.headers['etag'] == self.eTagBio:
        #    return r.headers['etag'], None
        if r.status_code != 200:
            print(r)
            return []
        xml = ET.fromstring(r.text)
        #self.eTagBio = r.headers['etag'] # WOULD BE NICE IF ETAGS WORKED GLOBE NEWSWIRE >:(
        return self.parseGlobe(xml)

    # How about no
    def prNewsWireBio(self, lastEtag = None):
        r = requests.head("https://www.prnewswire.com/rss/health-latest-news/health-latest-news-list.rss")
        if r.headers['Etag'] == lastEtag:
            r.close()
            return [r.headers['Etag'], None]
        r = requests.get("https://www.prnewswire.com/rss/health-latest-news/health-latest-news-list.rss")
        xml = ET.fromstring(r.text)
        etag = r.headers['etag']
        r.close()
        return etag, self.parse(xml)

    # updates once an hour - needs to be updated to work with class better
    def zacksNews(self):
        r = requests.get('http://feed.zacks.com/commentary/AllStories/rss')
        xml = ET.fromstring(r.text)
        parsed = self.parse(xml)
        retVal = []
        for i in parsed:
            retVal.append(i[i.find('h'):-3])
        parsed = []
        for i in range(len(retVal)):
            if i % 2 == 0:
                parsed.append(retVal[i])
        del parsed[-1]
        r.close()
        return [None, parsed]

    def parse(self, xml):
        stk = []
        links = []
        for child in xml:
            stk.append(child)
        while len(stk) > 0:
            child = stk.pop(-1)
            if child.tag == 'link':
                links.append(child.text)
            for children in child:
                stk.append(children)
        del links[-1]
        return links

    def parseGlobe(self, xml): # globe has a different structure. there might be a package out there that can process an
        stk = []                # rss feed better but for now this is fine.
        for child in xml:
            for grandchild in child:
                if grandchild.tag == 'item':
                    for item in grandchild:
                        if item.tag == 'link':
                            articleLink = item.text
                        if item.tag == 'pubDate':
                            date = item.text
                    stk.append((articleLink, date))
        return stk


class FB:
    def __init__(self):
        self.cred = credentials.Certificate('sentimentdatabase-firebase-adminsdk-u3ll8-f84d6f3c27.json')
        self.default_app = firebase_admin.initialize_app(self.cred)
        self.db = firestore.client(self.default_app)
        self.doc_ref = self.db.collection(u'Article')

    def getPrev(self):
        prev = {}
        for doc in self.doc_ref.where(u'time', u'>', time() - 86400 - 25200).stream():
            prev[doc.id] = doc.to_dict()['time']
        return prev

    def fireSave(self, key, value):
        self.doc_ref.document(key).set(value)
        if self.doc_ref.document(key).get().exists:
            return True
        return False


def allowedHoursWestCoast(currentTime):
    if currentTime.hour >= 1:
        return True
    if currentTime.hour < 17:
        return True
    return False


def allowedHoursEastCoast(currentTime):
    if currentTime.hour >= 4:
        return True
    if currentTime.hour < 20:
        return True
    return False

