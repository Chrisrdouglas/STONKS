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

fire = FB()
prev = fire.getPrev()
rss = RSS()

while True:

    while allowedHoursWestCoast(datetime.now()):#only run during preset hours
        globalPharma = rss.globalNewsWirePharma()
        startTime = time()
        #try:
        if globalPharma is not None and len(globalPharma) != 0:
            for links in globalPharma:
                link = links[0]
                dt = datetime.strptime(links[1], "%a, %d %b %Y %H:%M GMT") #Get time from rss feed
                timeDiscovered = int(dt.timestamp() - 25200) #adjust for eastcoast time
                h = hashlib.md5(link.encode()).hexdigest() #hash the link so we can use it as a key
                if h not in prev.keys() and allowedHoursEastCoast(dt): #do a check to make sure we haven't already saved it in firebase
                    # write to firebase
                    data = {u'link': link,
                            u'time': timeDiscovered}
                    if fire.fireSave(h, data):
                        prev[h] = timeDiscovered # associate the hash with the time discovered so we can delete it from our dict later

        globalBio = rss.globalNewsWireBio()

        if globalBio is not None and len(globalBio) != 0: # repeat above steps. Could have made this process into a
            for links in globalBio: #                       function. Chose to do that later so we can focus on other things.
                link = links[0]
                dt = datetime.strptime(links[1], "%a, %d %b %Y %H:%M GMT")
                timeDiscovered = int(dt.timestamp() - 25200)
                h = hashlib.md5(link.encode()).hexdigest()
                if h not in prev.keys() and allowedHoursEastCoast(dt):
                    # write to firebase
                    data = {u'link': link,
                            u'time': timeDiscovered}
                    if fire.fireSave(h, data):
                        prev[h] = timeDiscovered

        t = time()-startTime
        if t < 30:
            toDelete = [] # this is to prevent the dict from growing forever.
            for i in prev.keys():
                if time()-prev[i] > 604800: # if older than a week then delete
                    toDelete.append(i)
            for i in toDelete:
                del prev[i]
        sleep(30.0)

    sleep(300) #if we have a live day trading tool running this then this line has got to go
