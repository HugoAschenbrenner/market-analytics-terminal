# Financial Assumptions

## Data

The project uses synthetic/sample data only.

The bond dataset in `data/sample_bonds.csv` is artificial and designed for demonstration purposes. It does not represent real client positions, proprietary portfolios, or live market data.

## Bond Dataset Conventions

The sample bond dataset uses the following fields:

- `bond_id`: synthetic identifier
- `issuer`: synthetic issuer name
- `currency`: EUR or USD
- `coupon_rate`: annual coupon rate in decimal format, e.g. 5% = 0.05
- `maturity_date`: bond maturity date
- `issue_date`: synthetic issue date
- `frequency`: coupon frequency per year
- `clean_price`: clean price per 100 notional
- `yield_to_maturity`: annualized yield in decimal format
- `notional`: position notional
- `rating`: synthetic credit rating
- `sector`: broad issuer sector
- `spread_bps`: synthetic credit spread in basis points
- `curve_bucket`: maturity bucket used for DV01 decomposition

## Important Limitations

The dataset is built for analytics development and interview demonstration. It is not intended for valuation, trading, investment advice, or risk reporting on real portfolios.

Future fixed income calculations will use transparent approximations first. More advanced curve construction or QuantLib-based analytics may be added later.
