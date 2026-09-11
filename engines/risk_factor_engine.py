"""Transparent covariance, Gaussian VaR decomposition and curve PCA."""
import numpy as np
import pandas as pd
from scipy.stats import norm

def _matrix(data):
    x=np.asarray(data,dtype=float)
    if x.ndim!=2 or len(x)<2 or x.shape[1]<1 or not np.isfinite(x).all():
        raise ValueError('Risk observations must be a complete finite matrix with at least two rows.')
    return x

def covariance_estimate(data,method='sample',decay=.94):
    x=_matrix(data)
    if method not in ('sample','ewma','ledoit_wolf'):
        raise ValueError('Unsupported covariance estimator')
    active=np.std(x,axis=0)>1e-14
    result=np.zeros((x.shape[1],x.shape[1]))
    if not active.any():return result,0.
    a=x[:,active];n,p=a.shape;shrinkage=0.
    if method=='ewma':
        if not 0<decay<1:raise ValueError('EWMA decay must be between zero and one')
        weights=decay**np.arange(n-1,-1,-1);weights/=weights.sum()
        centered=a-weights@a
        covariance=(centered.T*weights)@centered/(1-weights@weights)
    else:
        centered=a-a.mean(axis=0)
        covariance=centered.T@centered/(n-1 if method=='sample' else n)
        if method=='ledoit_wolf':
            mu=np.trace(covariance)/p
            delta=np.sum((covariance-mu*np.eye(p))**2)/p
            beta=(np.sum((centered**2).T@(centered**2))/n-np.sum(covariance**2))/(p*n)
            shrinkage=float(np.clip(beta/delta,0,1)) if delta>0 else 0.
            covariance=(1-shrinkage)*covariance+shrinkage*mu*np.eye(p)
    result[np.ix_(active,active)]=covariance
    return result,shrinkage

def risk_statistics(pnl,confidence=.975,horizon=1,method='sample',quantities=None):
    x=_matrix(pnl)
    if not .5<confidence<1 or int(horizon)!=horizon or not 1<=horizon<len(x):
        raise ValueError('Invalid confidence or horizon')
    frame=pd.DataFrame(pnl)
    total=frame.sum(axis=1)
    horizon_pnl=total.rolling(int(horizon)).sum().dropna()
    q=horizon_pnl.quantile(1-confidence)
    historical_var=max(0.,-float(q))
    historical_es=max(0.,-float(horizon_pnl[horizon_pnl<=q].mean()))
    cov,shrinkage=covariance_estimate(x,method)
    variance=max(0.,cov.sum());sigma=np.sqrt(variance);z=norm.ppf(confidence)
    marginal_scale=z*np.sqrt(horizon)*cov.sum(axis=1)/sigma if sigma else np.zeros(x.shape[1])
    qties=np.ones(x.shape[1]) if quantities is None else np.asarray(quantities,dtype=float)
    if qties.shape!=(x.shape[1],) or not np.isfinite(qties).all():raise ValueError('Invalid quantities')
    marginal_unit=np.divide(marginal_scale,qties,out=np.zeros_like(qties),where=qties!=0)
    removal_variance=np.maximum(0.,variance-2*cov.sum(axis=1)+np.diag(cov))
    contributions=pd.DataFrame({'id':frame.columns,'component_var':marginal_scale,'marginal_var_per_unit':marginal_unit,
        'incremental_var':z*np.sqrt(horizon)*(sigma-np.sqrt(removal_variance)),
        'contribution':cov.sum(axis=1)/sigma if sigma else np.zeros(x.shape[1])})
    return dict(var=historical_var,es=historical_es,parametric_var=z*sigma*np.sqrt(horizon),
        parametric_es=norm.pdf(z)/(1-confidence)*sigma*np.sqrt(horizon),sigma=sigma,covariance=cov,
        shrinkage=shrinkage,contributions=contributions,horizon_pnl=horizon_pnl)

def backtest_var(pnl,confidence=.975,window=250):
    total=pd.Series(pnl,dtype=float)
    if window<2 or not .5<confidence<1 or not np.isfinite(total).all():raise ValueError('Invalid backtest inputs')
    threshold=(-total.shift(1).rolling(window).quantile(1-confidence)).clip(lower=0.)
    return pd.DataFrame({'pnl':total,'var':threshold,'exceedance':(-total>threshold)&threshold.notna()})

def curve_pca(history):
    x=_matrix(history)
    if x.shape[1]<3 or len(x)<5:raise ValueError('PCA requires three maturities and five observations')
    changes=np.diff(x,axis=0)*100  # input annual percent -> changes in bp
    centered=changes-changes.mean(axis=0)
    _,s,vt=np.linalg.svd(centered,full_matrices=False)
    variances=s*s/(len(centered)-1)
    for i in range(min(3,len(vt))):
        anchor=vt[i].sum() if i==0 else vt[i,-1]-vt[i,0] if i==1 else vt[i,len(vt[i])//2]-(vt[i,0]+vt[i,-1])/2
        if anchor<0:vt[i]*=-1
    explained=variances/variances.sum() if variances.sum() else np.zeros_like(variances)
    return {'loadings':vt[:3], 'variance':variances[:3], 'explained':explained[:3], 'scores':centered@vt[:3].T}
