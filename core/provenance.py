"""Common descriptive provenance for book context and saved analytical inputs.

`as_of`/`observed_at` identify the observation (or fixed demo date), never retrieval.
Missing historical metadata remains unknown; normalization invents no timestamp.
Public monitor DataResult/Quote already exposes the same concepts as typed fields.
"""
from datetime import datetime, timezone
import pandas as pd

DEMO_DATE = '2026-09-09'


def metadata(payload):
    source = payload.get('source', 'SYNTHETIC')
    return dict(
        source=source, provider=payload.get('provider', 'demo' if source == 'SYNTHETIC' else 'unknown'),
        as_of=payload.get('as_of', '—'), observed_at=payload.get('observed_at', payload.get('as_of', '—')),
        retrieved_at=payload.get('retrieved_at'), attempted_at=payload.get('attempted_at'),
        frequency=payload.get('frequency', 'fixed demonstration' if source == 'SYNTHETIC' else 'user assumption' if source == 'USER INPUT' else 'unspecified'),
        status=payload.get('status', 'synthetic' if source == 'SYNTHETIC' else 'user_input' if source == 'USER INPUT' else 'unverified'),
        cache_status=payload.get('cache_status', 'not applicable' if source != 'PUBLIC' else 'unknown'),
        cache_ttl_seconds=payload.get('cache_ttl_seconds'),
    )


def public_metadata(observed_at, provider, frequency='daily observation'):
    completed = datetime.now(timezone.utc).isoformat()
    return dict(source='PUBLIC', provider=provider, as_of=observed_at, observed_at=observed_at,
                retrieved_at=completed, attempted_at=completed, frequency=frequency, status='available',
                cache_status='retrieved', cache_ttl_seconds=900)


def observation_status(payload, now=None):
    """Retrieval success cannot make an old provider observation current."""
    info = metadata(payload)
    if info['source'] != 'PUBLIC' or info['status'] in ('stale', 'unavailable'):
        return info['status']
    observed = pd.to_datetime(info['observed_at'], utc=True, errors='coerce')
    if pd.isna(observed): return 'unverified'
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    if now.tzinfo is None: now = now.tz_localize('UTC')
    if observed > now + pd.Timedelta(minutes=5): return 'unverified'
    # Conservative calendar-day indication, not an exchange-calendar assertion.
    max_days = 62 if 'monthly' in info['frequency'] else 4
    return 'old' if (now - observed).total_seconds() > max_days*86400 else info['status']


def failed_refresh(previous, attempted_at):
    """Retain observation and last successful retrieval exactly."""
    result = {**previous, **metadata(previous), 'attempted_at': attempted_at}
    if result['source'] == 'PUBLIC': result.update(status='stale', cache_status='last success')
    return result
