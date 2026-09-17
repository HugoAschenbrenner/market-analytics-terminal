from math import exp, expm1, log, pi, sqrt

import numpy as np
import pytest
from scipy.integrate import quad

from engines.barrier_certificate_engine import barrier_snapshot, certificate_payoff, certificate_snapshot
from engines.options_pricing_engine import black_scholes_price


def bridge_integral(kind, direction, strike, barrier, rate, vol, dividend, maturity):
    """Independent numerical integration of terminal normal/Brownian bridge.

    Conditional no-touch probability is 1-exp(-2*x*y/(sigma²*T)).
    No closed-form normal moments from the pricing engine are used.
    """
    sign = 1 if direction == 'down' else -1
    x = sign * log(100 / barrier)
    mean = (rate - dividend - .5 * vol ** 2) * maturity
    sd = vol * sqrt(maturity)
    def integrand(z, payoff=True):
        terminal = 100 * exp(mean + sd * z)
        y = sign * log(terminal / barrier)
        survival = -expm1(-2 * x * y / sd ** 2) if y > 0 else 0.
        intrinsic = max((1 if kind == 'Call' else -1) * (terminal - strike), 0.) if payoff else 1.
        return exp(-z * z / 2) / sqrt(2 * pi) * survival * intrinsic
    knots = sorted([-12., 12.] + [z for p in [strike, barrier] if -12 < (z := (log(p / 100) - mean) / sd) < 12])
    value = sum(quad(integrand, a, b, epsabs=1e-11)[0] for a, b in zip(knots, knots[1:]))
    survival = sum(quad(lambda z: integrand(z, False), a, b, epsabs=1e-11)[0] for a, b in zip(knots, knots[1:]))
    return exp(-rate * maturity) * value, 1 - survival


@pytest.mark.parametrize('kind', ['Call', 'Put'])
@pytest.mark.parametrize('direction,barrier', [('down', 80.), ('up', 120.)])
@pytest.mark.parametrize('strike', [65., 80., 100., 120., 135.])
@pytest.mark.parametrize('rate,vol,dividend,maturity', [(.05,.3,0.,1.), (-.025,.6,.04,2.3), (.07,.12,.03,.04)])
def test_all_eight_barriers_against_independent_quadrature(kind, direction, barrier, strike, rate, vol, dividend, maturity):
    expected, touch = bridge_integral(kind, direction, strike, barrier, rate, vol, dividend, maturity)
    args = (100., strike, barrier, maturity, rate, vol, dividend)
    out = barrier_snapshot(kind, direction, 'out', *args)
    knock_in = barrier_snapshot(kind, direction, 'in', *args)
    assert out['price'] == pytest.approx(expected, abs=2e-9)
    assert out['touch_probability'] == pytest.approx(touch, abs=2e-11)
    assert out['price'] + knock_in['price'] == pytest.approx(black_scholes_price(kind,100,strike,maturity,rate,vol,dividend), abs=1e-10)


@pytest.mark.parametrize('direction,barrier', [('down',80.), ('up',120.)])
@pytest.mark.parametrize('kind', ['Call', 'Put'])
def test_touch_at_equality_and_history_are_irreversible(direction, barrier, kind):
    for spot, touched in [(barrier,False), (100.,True)]:
        value = barrier_snapshot(kind,direction,'out',spot,100.,barrier,1.,.05,.3,touched=touched)
        assert value['price'] == 0 and value['touched']
        assert value['touch_probability'] == 1
        assert value['knock_in'] == value['vanilla']


def test_expiry_deterministic_path_and_extreme_normal_tails():
    assert barrier_snapshot('Call','down','out',100,90,80,0,.05,.3)['price'] == 10
    assert barrier_snapshot('Call','up','out',100,90,102,1,.05,0)['price'] == 0
    far = barrier_snapshot('Put','down','out',100,105,1,1,-.03,1e-4,.08)
    assert far['price'] == pytest.approx(far['vanilla'], abs=1e-9)
    assert far['touch_probability'] == 0
    near = barrier_snapshot('Call','down','out',100,100,99.999999,1,.05,.3)
    assert 0 < near['price'] < 1e-5
    assert near['touch_probability'] > .999999


@pytest.mark.parametrize('field,value', [('spot',0),('strike',-1),('barrier',0),('maturity',-1),('volatility',-1),('rate',np.inf),('dividend',np.nan)])
def test_invalid_barrier_inputs(field,value):
    args = dict(spot=100,strike=100,barrier=80,maturity=1,rate=.03,volatility=.2,dividend=0.)
    args[field] = value
    with pytest.raises(ValueError):
        barrier_snapshot('Call','down','out',**args)


@pytest.mark.parametrize('kind', ['discount','bonus','capped_bonus'])
@pytest.mark.parametrize('touched', [False, True])
def test_certificate_redemptions_and_replication(kind,touched):
    terminal = np.array([0.,60.,70.,70.01,90.,110.,120.,150.])
    result = certificate_payoff(kind,terminal,touched=touched)
    if kind == 'discount':
        expected = np.minimum(terminal,120)
    else:
        expected = terminal + np.where(touched | (terminal<=70),0,np.maximum(110-terminal,0))
        if kind=='capped_bonus':
            expected -= np.maximum(terminal-120,0)
    assert result == pytest.approx(expected)
    snapshot = certificate_snapshot(kind,100,1,.03,.25,.04,touched=touched)
    assert snapshot['price'] == pytest.approx(sum(snapshot['components'].values()))
    assert snapshot['components']['prepaid'] == pytest.approx(100*exp(-.04))
    if kind != 'discount' and touched:
        assert snapshot['components']['bonus_put'] == 0


def test_bonus_is_not_a_free_floor_and_discount_is_a_bond_minus_put():
    bonus = certificate_snapshot('bonus',100,1,.03,.25)
    assert bonus['price'] > 100  # with q=0, adding a valuable floor costs money
    discount = certificate_snapshot('discount',100,1,.03,.25,.04,cap=105)
    expected = 105*exp(-.03)-black_scholes_price('Put',100,105,1,.03,.25,.04)
    assert discount['price'] == pytest.approx(expected)
    assert certificate_snapshot('bonus',70,0,.03,.25)['price'] == 70
    assert certificate_snapshot('bonus',100,0,.03,.25)['price'] == 110


@pytest.mark.parametrize('kwargs', [dict(kind='unknown'),dict(kind='bonus',barrier=110),dict(kind='capped_bonus',cap=105),dict(kind='bonus',level=np.nan)])
def test_invalid_certificate_terms(kwargs):
    with pytest.raises(ValueError):
        certificate_snapshot(spot=100,maturity=1,rate=.03,volatility=.2,**kwargs)
