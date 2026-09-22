"""Public RSS and official calendars, shared across News, Security, World and Board."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime,timezone,timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlencode,urlparse,urlunparse
from zoneinfo import ZoneInfo
import re
import xml.etree.ElementTree as ET
from core.market_contracts import NewsArticle,Event
from core.securities import SECURITIES
from services.market_monitor import get_market_service,request_text

UTC=timezone.utc
FEEDS={
 'Fed':('https://www.federalreserve.gov/feeds/press_all.xml','Federal Reserve','Central Banks','Americas'),
 'ECB':('https://www.ecb.europa.eu/rss/press.html','ECB','Central Banks','Europe'),
}
CALENDARS={
 'BLS':('https://www.bls.gov/schedule/news_release/bls.ics','https://www.bls.gov/schedule/'),
 'BEA':('https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics','https://www.bea.gov/news/schedule'),
}

class _Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,data):self.parts.append(data)

def plain(value,limit=500):
    parser=_Text();parser.feed(unescape(str(value or '')))
    return re.sub(r'\s+',' ',' '.join(parser.parts)).strip()[:limit]

def safe_url(value):
    try:
        parsed=urlparse(str(value or ''))
        if parsed.scheme not in ('https','http') or not parsed.hostname or parsed.username or parsed.password:return ''
        return urlunparse(parsed._replace(fragment=''))
    except ValueError:return ''

def parse_rss(text,source,category='Macro',region='Global',security_id=''):
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():raise ValueError('Unsupported feed entities')
    root=ET.fromstring(text)
    if root.tag.split('}')[-1] not in ('rss','RDF','feed'):raise ValueError('Not a news feed')
    items=[]
    for item in root.findall('.//item')[:60]:
        title=plain(item.findtext('title'),250);url=safe_url(item.findtext('link'))
        if not title or not url:continue
        try:stamp=parsedate_to_datetime(item.findtext('pubDate','')).astimezone(UTC)
        except (TypeError,ValueError,OverflowError):stamp=None
        if stamp and stamp>datetime.now(UTC)+timedelta(minutes=10):continue
        publisher=plain(item.findtext('source'),100) or source
        items.append(NewsArticle(title,publisher,stamp,url,plain(item.findtext('description'),220),(security_id,) if security_id else (),category,region))
    return items


def feed(key):
    if key in SECURITIES:
        s=SECURITIES[key]
        url='https://feeds.finance.yahoo.com/rss/2.0/headline?'+urlencode({'s':s.symbol,'region':'US','lang':'en-US'})
        source='Yahoo Finance RSS';category=s.asset_class;region=s.region;id=key
    else:url,source,category,region=FEEDS[key];id=''
    return get_market_service().cache.get(('news',key),lambda:parse_rss(request_text(url),source,category,region,id),ttl=600)


def collect_news(keys):
    keys=list(dict.fromkeys(keys))[:12]
    with ThreadPoolExecutor(max_workers=6) as pool:results=dict(zip(keys,pool.map(feed,keys)))
    articles={}
    for result in results.values():
        for article in result.value or []:
            # Ignore tracking query parameters when deduplicating syndication.
            identity=urlunparse(urlparse(article.url)._replace(query=''))
            if identity in articles:
                old=articles[identity];article=replace(old,securities=tuple(dict.fromkeys(old.securities+article.securities)))
            articles[identity]=article
    return sorted(articles.values(),key=lambda a:a.published_at or datetime.min.replace(tzinfo=UTC),reverse=True),results


def parse_ics(text,source,url):
    if 'BEGIN:VCALENDAR' not in text:raise ValueError('Not an iCalendar')
    lines=re.sub(r'\r?\n[ \t]','',text).splitlines();records=[];record=None
    for line in lines:
        if line=='BEGIN:VEVENT':record={}
        elif line=='END:VEVENT':
            if record is not None:records.append(record)
            record=None
        elif record is not None and ':' in line:
            key,value=line.split(':',1);record[key]=value
    events=[]
    for record in records:
        if record.get('STATUS')=='CANCELLED' or 'RRULE' in record:continue
        start=next(((k,v) for k,v in record.items() if k.split(';')[0]=='DTSTART'),None)
        if not start or not record.get('SUMMARY'):continue
        key,value=start
        try:
            zone=UTC if value.endswith('Z') else ZoneInfo(re.search(r'TZID=([^;]+)',key).group(1)) if 'TZID=' in key else ZoneInfo('America/New_York')
            when=datetime.strptime(value.rstrip('Z'),'%Y%m%dT%H%M%S' if 'T' in value else '%Y%m%d').replace(tzinfo=zone).astimezone(UTC)
        except (ValueError,AttributeError,KeyError):continue
        title=plain(record['SUMMARY'].replace('\\,',',').replace('\\n',' '),250)
        events.append(Event(title,when,source,safe_url(record.get('URL')) or url,timing='date only' if 'T' not in value else 'scheduled'))
    return sorted(events,key=lambda e:e.when)


def macro_events():
    def load(key):
        feed_url,url=CALENDARS[key]
        return get_market_service().cache.get(('events',key),lambda:parse_ics(request_text(feed_url),key,url),ttl=21600)
    with ThreadPoolExecutor(max_workers=2) as pool:results=dict(zip(CALENDARS,pool.map(load,CALENDARS)))
    return sorted([e for r in results.values() for e in (r.value or [])],key=lambda e:e.when),results


def corporate_events(id):
    result=get_market_service().raw_chart(id);events=[]
    if result.value:
        for kind,items in result.value[2].items():
            if kind not in ('dividends','splits'):continue
            for item in items.values():
                try:
                    when=datetime.fromtimestamp(float(item['date']),UTC)
                    title=f'{id} · '+(f'Dividend {float(item["amount"]):g} {SECURITIES[id].currency}' if kind=='dividends' else f'Split {item["splitRatio"]}')
                    events.append(Event(title,when,'Yahoo Finance chart events','https://finance.yahoo.com/quote/'+SECURITIES[id].symbol+'/',id,'reported date'))
                except (KeyError,TypeError,ValueError,OverflowError):continue
    return sorted(events,key=lambda e:e.when,reverse=True),result
