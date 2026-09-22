from datetime import timezone
from services.market_news import parse_rss,parse_ics,safe_url,plain
import pytest

def test_rss_sanitizes_markup_and_rejects_unsafe_links():
    text='''<rss><channel><item><title>&lt;b&gt;News&lt;/b&gt;</title><link>https://example.com/news</link><pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate><description>&lt;p&gt;Hello&lt;/p&gt;</description></item><item><title>Bad</title><link>javascript:alert(1)</link></item></channel></rss>'''
    items=parse_rss(text,'Provider',security_id='NVDA')
    assert len(items)==1 and items[0].headline=='News' and items[0].description=='Hello'
    assert items[0].securities==('NVDA',) and items[0].published_at.tzinfo==timezone.utc
    assert safe_url('https://user:secret@example.com')==''
    assert safe_url('file:///etc/passwd')==''

def test_invalid_date_does_not_invent_publication_time():
    items=parse_rss('<rss><channel><item><title>Title</title><link>https://example.com</link></item></channel></rss>','Test')
    assert items[0].published_at is None

@pytest.mark.parametrize('month,utc_hour',[('01',13),('07',12)])
def test_ics_respects_new_york_dst_and_unfolds_lines(month,utc_hour):
    text=f'''BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;TZID=America/New_York:2026{month}15T083000
SUMMARY:CPI release
 continued
END:VEVENT
END:VCALENDAR'''
    events=parse_ics(text,'BLS','https://www.bls.gov')
    assert len(events)==1 and events[0].when.hour==utc_hour
    assert events[0].title=='CPI releasecontinued'

def test_ics_rejects_html_and_skips_cancelled_or_recurring_events():
    with pytest.raises(ValueError):parse_ics('<html>Forbidden</html>','BLS','')
    assert parse_ics('BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:20260715T120000Z\nSUMMARY:Test\nSTATUS:CANCELLED\nEND:VEVENT\nEND:VCALENDAR','BLS','')==[]
