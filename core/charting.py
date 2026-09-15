"""Theme-aware Plotly charts with room for labels, legends and color bars."""
import streamlit as st
from plotly.colors import qualitative
from core.theme import TOKENS
from core.state import get_state


def style_figure(fig, theme="dark", height=290):
    c = TOKENS[theme]
    palette=[c['accent'],c['violet'],c['positive'],c['warning'],c['negative']]
    replacements={old.lower():palette[i % len(palette)] for i,old in enumerate(qualitative.Plotly)}
    # Streamlit injects temporary categorical colors before rendering. Resolve
    # them here because this application owns the theme (theme=None).
    replacements.update({f'#{i+1:06d}':palette[i % len(palette)] for i in range(10)})
    scale=fig.layout.coloraxis.colorscale
    if scale and any(str(color).startswith('#0000') for _,color in scale):
        fig.update_layout(coloraxis_colorscale='Viridis')
    for tokens in TOKENS.values():
        for i,key in enumerate(['accent','violet','positive','warning','negative']):
            replacements[tokens[key].lower()]=palette[i]
    for shape in fig.layout.shapes:
        if shape.line.color in ('#eabc63',TOKENS['dark']['warning'],TOKENS['light']['warning']):shape.line.color=c['warning']
        if shape.line.color in ('#ff6b7b',TOKENS['dark']['negative'],TOKENS['light']['negative']):shape.line.color=c['negative']
    for trace in fig.data:
        for attr in ('marker','line'):
            obj=getattr(trace,attr,None)
            color=getattr(obj,'color',None)
            if isinstance(color,str) and color.lower() in replacements:
                obj.color=replacements[color.lower()]
        if trace.type=='waterfall':
            trace.update(increasing=dict(marker_color=c['positive']),decreasing=dict(marker_color=c['negative']),totals=dict(marker_color=c['accent']))
        if trace.type in ('heatmap','surface'):
            trace.update(colorbar=dict(thickness=12,len=.75,tickfont=dict(color=c['text_primary']),title=dict(font=dict(color=c['text_primary']))))
    # Reserve extra vertical room for horizontal legends below the axis labels.
    legend_count=sum(bool(trace.name) and trace.showlegend is not False for trace in fig.data)
    legend_count+=sum(shape.showlegend is True for shape in fig.layout.shapes)
    orientation=fig.layout.legend.orientation or 'h'
    extra=max(25,18*legend_count) if orientation=='v' and legend_count else 55 if legend_count>3 else 25 if legend_count else 0
    fig.update_layout(template="plotly_dark" if theme == "dark" else "plotly_white", height=height+extra,
        margin=dict(l=14,r=22,t=48,b=48+extra),paper_bgcolor=c['chart_background'],plot_bgcolor=c['chart_background'],
        font=dict(color=c['text_primary'],family="Inter, Arial, sans-serif",size=12),colorway=palette,
        hoverlabel=dict(bgcolor=c['surface'],font_color=c['text_primary']),
        title=dict(font=dict(size=14,color=c['text_primary']),automargin=True),
        legend=dict(orientation=orientation,yanchor='top',y=-.3,x=0,font=dict(size=10,color=c['text_primary']),title_text=''),
        coloraxis_colorbar=dict(thickness=12,len=.75,tickfont=dict(color=c['text_primary'])),
        scene=dict(bgcolor=c['chart_background'],xaxis=dict(backgroundcolor=c['surface'],gridcolor=c['grid'],color=c['text_primary']),yaxis=dict(backgroundcolor=c['surface'],gridcolor=c['grid'],color=c['text_primary']),zaxis=dict(backgroundcolor=c['surface'],gridcolor=c['grid'],color=c['text_primary'])))
    fig.update_xaxes(gridcolor=c['grid'],zerolinecolor=c['border'],automargin=True,title_standoff=10)
    fig.update_yaxes(gridcolor=c['grid'],zerolinecolor=c['border'],automargin=True,title_standoff=10)
    return fig


def chart(fig, key=None, height=290):
    from core.i18n import t
    from core.models import ASSET_CLASSES
    for trace in fig.data:
        if trace.name in ASSET_CLASSES:trace.name=t(trace.name)
    st.plotly_chart(style_figure(fig,get_state().ui.theme,height),width="stretch",key=key,theme=None,
        config={'displayModeBar':False,'responsive':True,'scrollZoom':False})
