"""Exchange-local regular schedules, DST-aware; holidays are explicitly unverified."""
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

def session_state(session,now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(ZoneInfo(session.timezone))
    periods=[(time.fromisoformat(a),time.fromisoformat(b)) for a,b in session.periods]
    opened=now.weekday()<5 and any(a<=now.time().replace(tzinfo=None)<b for a,b in periods)
    boundaries=[]
    for offset in range(8):
        day=now.date()+timedelta(days=offset)
        if day.weekday()>4:continue
        for a,b in periods:
            for edge in ([b] if opened and offset==0 else [a]):
                boundary=datetime.combine(day,edge,tzinfo=now.tzinfo)
                if boundary>now:boundaries.append(boundary)
    next_time=min(boundaries)
    seconds=(next_time.astimezone(timezone.utc)-now.astimezone(timezone.utc)).total_seconds()
    return {'local':now,'scheduled_open':opened,'next':next_time,'minutes':int(seconds//60)}
