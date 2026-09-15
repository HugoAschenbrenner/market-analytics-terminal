from copy import deepcopy
import plotly.express as px
import plotly.graph_objects as go
import pytest
from core.charting import style_figure
from core.theme import TOKENS


def luminance(hex_color):
    rgb=[int(hex_color[i:i+2],16)/255 for i in (1,3,5)]
    linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    return sum(a*b for a,b in zip(linear,[.2126,.7152,.0722]))


@pytest.mark.parametrize('theme',['dark','light'])
def test_theme_text_and_status_colors_have_readable_contrast(theme):
    tokens=TOKENS[theme]
    for surface in ['background','surface','surface_secondary']:
        bg=luminance(tokens[surface])
        for name in ['text_primary','text_secondary','accent','positive','negative','warning']:
            fg=luminance(tokens[name]);ratio=(max(bg,fg)+.05)/(min(bg,fg)+.05)
            assert ratio>=4.5,(theme,surface,name,ratio)


def test_plotly_express_theme_switch_preserves_data_and_updates_colors():
    fig=px.bar(x=['A','B'],y=[1,-2],color=['one','two'])
    values=[deepcopy(trace.y) for trace in fig.data]
    style_figure(fig,'dark');style_figure(fig,'light')
    assert fig.data[0].marker.color==TOKENS['light']['accent']
    assert fig.data[1].marker.color==TOKENS['light']['violet']
    for trace,expected in zip(fig.data,values):assert list(trace.y)==list(expected)
    assert fig.layout.font.color==TOKENS['light']['text_primary']


@pytest.mark.parametrize('theme',['dark','light'])
def test_waterfalls_and_surfaces_use_semantic_theme_colors(theme):
    fig=go.Figure(go.Waterfall(x=['gain','loss','total'],y=[10,-5,5]))
    style_figure(fig,theme)
    assert fig.data[0].increasing.marker.color==TOKENS[theme]['positive']
    assert fig.data[0].decreasing.marker.color==TOKENS[theme]['negative']
    fig=go.Figure(go.Surface(z=[[1,2],[3,4]]));style_figure(fig,theme)
    assert fig.layout.scene.xaxis.color==TOKENS[theme]['text_primary']
