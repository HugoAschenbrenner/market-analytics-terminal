"""Exchange-local regular schedules, DST-aware; verified NYSE dates; other holiday calendars are explicitly unverified."""
from dataclasses import dataclass
from datetime import datetime,time,timedelta,timezone
from zoneinfo import ZoneInfo

@dataclass(frozen=True)
class MarketSession:
    city:str
    timezone:str
    periods:tuple

SESSIONS=(
 MarketSession('New York','America/New_York',(('09:30','16:00'),)),
 MarketSession('London','Europe/London',(('08:00','16:30'),)),
 MarketSession('Paris','Europe/Paris',(('09:00','17:30'),)),
 MarketSession('Tokyo','Asia/Tokyo',(('09:00','11:30'),('12:30','15:30'))),
 MarketSession('Hong Kong','Asia/Hong_Kong',(('09:30','12:00'),('13:00','16:00'))),
 MarketSession('Singapore','Asia/Singapore',(('09:00','12:00'),('13:00','17:00'))),
 MarketSession('Sydney','Australia/Sydney',(('10:00','16:00'),)),
)

# Published NYSE cash-equity calendar, verified 2026-09-22. No extrapolation.
# https://www.nyse.com/trade/hours-calendars
NYSE_HOLIDAYS={
 2026:('01-01','01-19','02-16','04-03','05-25','06-19','07-03','09-07','11-26','12-25'),
 2027:('01-01','01-18','02-15','03-26','05-31','06-18','07-05','09-06','11-25','12-24'),
 2028:('01-17','02-21','04-14','05-29','06-19','07-04','09-04','11-23','12-25'),
}
NYSE_EARLY={2026:('11-27','12-24'),2027:('11-26',),2028:('07-03','11-24')}

def periods_on(session,day):
    if day.weekday()>4:return []
    if session.city=='New York' and day.year in NYSE_HOLIDAYS:
        md=day.strftime('%m-%d')
        if md in NYSE_HOLIDAYS[day.year]:return []
        if md in NYSE_EARLY[day.year]:return [(time(9,30),time(13))]
    return [(time.fromisoformat(a),time.fromisoformat(b)) for a,b in session.periods]


def session_state(session,now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(ZoneInfo(session.timezone))
    periods=periods_on(session,now.date())
    opened=any(a<=now.time().replace(tzinfo=None)<b for a,b in periods)
    boundaries=[]
    for offset in range(10):
        day=now.date()+timedelta(days=offset)
        for a,b in periods_on(session,day):
            for edge in ([b] if opened and offset==0 else [a]):
                boundary=datetime.combine(day,edge,tzinfo=now.tzinfo)
                if boundary>now:boundaries.append(boundary)
    next_time=min(boundaries)
    seconds=(next_time.astimezone(timezone.utc)-now.astimezone(timezone.utc)).total_seconds()
    return {'local':now,'scheduled_open':opened,'next':next_time,'minutes':int(seconds//60),
            'periods':periods,'holiday_verified':session.city=='New York' and now.year in NYSE_HOLIDAYS}
