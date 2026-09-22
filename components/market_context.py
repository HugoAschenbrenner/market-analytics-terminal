import html
from datetime import datetime,timezone,timedelta
import streamlit as st
from core.monitor_copy import tr
from core.securities import SECURITIES,peers
from core.market_formatting import number,large,finite
from services.market_monitor import get_market_service
from services.market_news import collect_news,macro_events,corporate_events,CALENDARS


def news_panel(keys,key,query='',category='All',region=None,limit=10,order='newest'):
    from components.global_header import open_security
    articles,results=collect_news(keys)
    articles=[a for a in articles if (category=='All' or a.category==category) and (not region or a.region in (region,'Global')) and (not query or query.lower() in (a.headline+' '+a.description).lower())]
    if order=='relevance' and query:
        articles.sort(key=lambda a:(a.headline.lower().count(query.lower())*2+a.description.lower().count(query.lower())),reverse=True)
    if not articles:st.info(tr('No matching verified headlines. Feeds may be unavailable or contain no matching stories.','Aucun titre vérifié correspondant. Les flux peuvent être indisponibles ou ne contenir aucun résultat.'))
    for i,article in enumerate(articles[:limit]):
        stamp=article.published_at.strftime('%Y-%m-%d %H:%M UTC') if article.published_at else tr('Publication time unavailable','Date de publication indisponible')
        st.markdown(f'<div class="news-story"><a href="{html.escape(article.url,quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(article.headline)}</a><div class="monitor-note">{html.escape(article.source)} · {stamp}</div><p class="monitor-note">{html.escape(article.description)}</p></div>',unsafe_allow_html=True)
        if article.securities:
            cols=st.columns(min(len(article.securities),4))
            for j,id in enumerate(article.securities[:4]):cols[j].button(id,key=f'{key}_tag_{i}_{id}',on_click=open_security,args=(id,))
    stale=[name for name,r in results.items() if r.status=='stale'];missing=[name for name,r in results.items() if r.value is None]
    if stale:st.caption(tr('Cached headlines; refresh failed: ','Titres conservés ; actualisation échouée : ')+', '.join(stale))
    if missing:st.caption(tr('Feeds unavailable: ','Flux indisponibles : ')+', '.join(missing))
    st.caption(tr('Public RSS, cached 10 min. Instrument tags identify the provider feed, not an editorial endorsement or a relevance score.','Flux RSS publics, cache 10 min. Les étiquettes désignent le flux du fournisseur, pas une recommandation ni un score de pertinence.'))


def events_panel(id=None):
    now=datetime.now(timezone.utc)
    if id and SECURITIES[id].asset_class in ('Equities','ETFs'):
        events,result=corporate_events(id)
        st.caption(tr('Reported dividends and splits','Dividendes et splits publiés'))
        recent=[e for e in events if now-timedelta(days=366)<=e.when<=now+timedelta(days=180)]
        if not recent:st.info(tr('No verified corporate events available.','Aucun événement d’entreprise vérifié disponible.'))
        for event in recent[:10]:st.write(f'{event.when:%Y-%m-%d} · {event.title}')
        st.caption(tr('Provider-reported dates; confirm on the issuer’s investor-relations page. Earnings dates are shown in Fundamentals when supplied.','Dates publiées par le fournisseur ; à confirmer auprès des relations investisseurs. Les résultats figurent dans Fondamentaux si une date est fournie.'))
        if result.status=='stale':st.caption(tr('Event feed retained from the last successful request.','Événements conservés de la dernière requête réussie.'))
    events,results=macro_events()
    upcoming=[e for e in events if now<=e.when<=now+timedelta(days=90)]
    st.caption(tr('Upcoming official US releases · next 90 days','Prochaines publications officielles US · 90 jours'))
    if not upcoming:st.info(tr('No verified upcoming release available from the calendar feeds. Consult the official schedules below.','Aucune publication à venir vérifiée dans les flux. Consultez les calendriers officiels ci-dessous.'))
    for event in upcoming[:12]:st.write(f'{event.when:%Y-%m-%d %H:%M UTC} · {event.title} · {event.source}')
    if any(r.status=='stale' for r in results.values()):st.warning(tr('Calendar refresh failed; dates may have changed.','Actualisation du calendrier échouée ; les dates ont pu changer.'))
    for name,(_,url) in CALENDARS.items():st.link_button(name+' · '+tr('official calendar','calendrier officiel'),url)
    st.link_button('FOMC · '+tr('meeting calendar','calendrier des réunions'),'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm')
    st.link_button('ECB · '+tr('meeting calendar','calendrier des réunions'),'https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html')


def fundamentals_panel(id):
    result=get_market_service().fundamentals(id)
    if result.value is None:
        st.info(tr('Fundamentals unavailable from the public provider. No ratios are estimated.','Fondamentaux indisponibles auprès du fournisseur public. Aucun ratio estimé.'));return
    fields=result.value.fields
    st.caption(result.value.source+f' · {result.status} · '+(f'{result.retrieved_at:%Y-%m-%d %H:%M UTC}' if result.retrieved_at else ''))
    st.write(' · '.join(str(fields[k]) for k in ('country','sector','industry') if k in fields))
    if fields.get('longBusinessSummary'):
        with st.expander(tr('About the company / fund','À propos de la société / du fonds')):st.write(fields['longBusinessSummary'])
    items=[(tr('Market cap','Capitalisation'),large(fields.get('marketCap'))),(tr('Trailing P/E','PER historique'),number(fields.get('trailingPE'))),(tr('EPS','BPA'),number(fields.get('trailingEps'))),('Beta',number(fields.get('beta'))),(tr('Revenue','Chiffre d’affaires'),large(fields.get('totalRevenue'))),(tr('Net income','Résultat net'),large(fields.get('netIncomeToCommon')))]
    st.dataframe([{tr('Metric','Mesure'):label,tr('Value','Valeur'):value} for label,value in items],hide_index=True,width='stretch')
    st.caption(tr('Financial reporting currency: ','Devise comptable : ')+str(fields.get('financialCurrency','—')))
    st.caption(tr('Monetary figures use the provider’s financial reporting currency, which can differ from the listing currency. Reporting periods and beta methodology depend on the provider.','Montants dans la devise comptable du fournisseur, qui peut différer de la devise de cotation. Périodes et méthode du bêta dépendent du fournisseur.'))
    q=get_market_service().quote(id).value
    if q and q.price>0 and finite(fields.get('trailingAnnualDividendRate')):
        st.metric(tr('Trailing cash-dividend yield (calculated)','Rendement des dividendes passés (calculé)'),number(float(fields['trailingAnnualDividendRate'])/q.price*100)+'%')
        st.caption(tr('Provider annual cash dividend per share ÷ observed share price; not a forward dividend promise.','Dividende annuel passé par action du fournisseur ÷ cours observé ; pas une promesse de dividende futur.'))
    if finite(fields.get('earningsTimestamp')):
        stamp=datetime.fromtimestamp(float(fields['earningsTimestamp']),timezone.utc)
        st.caption(tr('Provider earnings timestamp (may be historical / provisional): ','Date de résultats du fournisseur (historique / provisoire possible) : ')+f'{stamp:%Y-%m-%d %H:%M UTC}')
    from components.global_header import open_security
    st.caption(tr('Directory peers · same asset class, not a valuation peer selection','Voisins de l’annuaire · même classe, pas une sélection de comparables de valorisation'))
    cols=st.columns(3)
    for i,peer in enumerate(peers(SECURITIES[id],3)):cols[i].button(peer,key='fund_peer_'+peer,on_click=open_security,args=(peer,))
