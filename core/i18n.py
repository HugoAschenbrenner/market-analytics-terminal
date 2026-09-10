"""Single translation catalog. Stable codes are kept separate from visible labels."""
STRINGS = {
 "workspaces": ("Workspaces", "Espaces de travail"),
 "book.nav": ("Net asset value must be positive after financing liabilities.", "La valeur liquidative doit être positive après dettes de financement."),
 "nav.overview": ("Desk Overview", "Vue du desk"), "nav.markets": ("Markets", "Marchés"),
 "nav.risk": ("Risk Lab", "Laboratoire de risque"), "nav.derivatives": ("Derivatives Lab", "Dérivés"), "nav.financing": ("Financing", "Financement"),
 "brand": ("MARKET ANALYTICS / DESK", "MARKET ANALYTICS / DESK"),
 "subtitle": ("Market → Position → Risk → Scenario → Hedge → Decision", "Marché → Position → Risque → Scénario → Couverture → Décision"),
 "language": ("Language", "Langue"), "theme": ("Theme", "Thème"), "dark": ("Dark", "Sombre"), "light": ("Light", "Clair"),
 "status": ("Market context", "Contexte de marché"), "SYNTHETIC": ("SYNTHETIC", "SYNTHÉTIQUE"), "PUBLIC": ("PUBLIC", "PUBLIC"), "USER INPUT": ("USER INPUT", "SAISIE UTILISATEUR"),
 "book": ("Position book", "Portefeuille"), "book.selector": ("Demo book", "Portefeuille démo"),
 "book.balanced": ("Multi-Asset Balanced", "Multi-actifs équilibré"), "book.macro": ("Rates & FX Macro", "Macro Taux & Change"),
 "book.options": ("Equity Options Book", "Options actions"), "book.structured": ("Structured / Hedged Book", "Structurés / Couverture"),
 "book.edit": ("Edit book", "Modifier le portefeuille"), "book.load": ("Load custom book", "Charger un portefeuille"),
 "book.apply": ("Apply positions", "Appliquer les positions"), "book.csv": ("Import CSV", "Importer CSV"),
 "book.template": ("Download current book CSV", "Télécharger le portefeuille CSV"), "book.saved": ("Book updated across all workspaces.", "Portefeuille mis à jour dans tous les espaces."),
 "book.note": ("Quantities determine exposures. Options are marked from shared market inputs; bonds use quoted clean price. Optional weights must reconcile to calculated NAV. Up to 1,000 positions.", "Les quantités déterminent les expositions. Options valorisées avec les données partagées ; obligations au prix pied de coupon saisi. Les poids facultatifs doivent correspondre à la VL calculée. Jusqu’à 1 000 positions."),
 "book.missing_columns": ("Required columns: id, ticker, asset_class, currency, quantity, price.", "Colonnes requises : id, ticker, asset_class, currency, quantity, price."),
 "book.row_count": ("The book must contain 1–1,000 positions.", "Le portefeuille doit contenir de 1 à 1 000 positions."),
 "book.missing_values": ("Required fields cannot be empty.", "Les champs requis ne peuvent pas être vides."),
 "book.duplicates": ("Position identifiers must be unique; tickers may repeat for separate contracts.", "Les identifiants doivent être uniques ; un ticker peut désigner plusieurs contrats."),
 "book.asset_class": ("Unsupported asset class.", "Classe d’actifs non prise en charge."), "book.currency": ("Unsupported currency.", "Devise non prise en charge."),
 "book.numeric": ("Numeric fields must be finite numbers.", "Les champs numériques doivent contenir des nombres finis."),
 "book.positive": ("Prices, multipliers, maturities, strikes and volatilities must be positive.", "Prix, multiplicateurs, maturités, strikes et volatilités doivent être positifs."),
 "book.option_type": ("Option type must be Call or Put.", "Le type d’option doit être Call ou Put."),
 "book.weights": ("Optional weights must be complete, sum to 1, and match quantity-based exposures.", "Les poids facultatifs doivent être complets, totaliser 1 et correspondre aux quantités."),
 "book.underlying": ("An option underlying is missing from shared market inputs.", "Un sous-jacent d’option est absent des données de marché partagées."),
 "error": ("Calculation could not be completed. Check the inputs.", "Calcul impossible. Vérifiez les paramètres."),
 "data": ("View data", "Voir les données"), "details": ("Calculation details", "Détails du calcul"), "methodology": ("Methodology & formulas", "Méthodologie & formules"),
 "about": ("Build & assumptions", "Projet & hypothèses"),
 "disclaimer": ("Educational / proxy analytics. Hypothetical scenarios, not forecasts. No regulatory compliance or bank-grade pricing claim.", "Analyses pédagogiques / approximatives. Scénarios hypothétiques, pas des prévisions. Aucune conformité réglementaire ni valorisation bancaire revendiquée."),
 "author": ("Built by Hugo Aschenbrenner · SKEMA MSc Financial Markets & Investments", "Créé par Hugo Aschenbrenner · SKEMA MSc Financial Markets & Investments"),
 "nav": ("NAV", "VL"), "gross": ("Gross exposure", "Exposition brute"), "dv01": ("Net DV01 / bp", "DV01 nette / pb"),
 "delta": ("Delta · spot units", "Delta · unités spot"), "delta_cash": ("Delta equivalent", "Équivalent Delta"), "gamma": ("Gamma", "Gamma"), "vega": ("Vega / vol pt", "Vega / point de vol"),
 "value": ("Value", "Valeur"), "exposure": ("Exposure", "Exposition"), "asset_class": ("Asset class", "Classe d’actifs"),
 "position": ("Position", "Position"), "currency": ("Currency", "Devise"), "base_currency": ("Base currency", "Devise de référence"),
 "concentration": ("Book concentration", "Concentration du portefeuille"), "risk_contribution": ("Volatility contribution", "Contribution à la volatilité"),
 "top_risks": ("Top risks · calculated from this book", "Risques majeurs · calculés sur ce portefeuille"),
 "insight.concentration": ("{asset} represents {weight:.1%} of gross exposure.", "{asset} représente {weight:.1%} de l’exposition brute."),
 "insight.dv01": ("{share:.1%} of absolute DV01 sits at 10 years or longer.", "{share:.1%} de la DV01 absolue est située à 10 ans ou plus."),
 "insight.gamma": ("Net Gamma is {gamma:,.1f}; Delta changes by this amount per 1-unit spot move.", "Gamma net : {gamma:,.1f} ; variation du Delta pour un mouvement de spot de 1 unité."),
 "insight.fx": ("{share:.1%} of gross exposure is outside {currency}.", "{share:.1%} de l’exposition brute est hors {currency}."),
 "rates": ("Rates & Credit", "Taux & Crédit"), "fx": ("FX", "Change"), "equity_vol": ("Equity & Volatility", "Actions & Volatilité"),
 "curve": ("Yield curves", "Courbes de taux"), "tenor": ("Maturity (years)", "Maturité (années)"), "yield": ("Yield (%)", "Taux (%)"),
 "spot": ("Spot", "Spot"), "rate": ("Rate (%)", "Taux (%)"), "vol": ("Volatility (%)", "Volatilité (%)"),
 "book_exposure": ("Book & Exposure", "Positions & Expositions"), "risk_var": ("VaR / Expected Shortfall", "VaR / Perte moyenne extrême"),
 "factor": ("Factor Risk", "Risque factoriel"), "stress": ("Stress & Scenario", "Stress & Scénarios"), "validation": ("Validation / P&L Explain", "Validation / Explication du P&L"),
 "vanilla": ("Vanilla Options", "Options vanilles"), "greeks": ("Greeks", "Sensibilités"), "volatility": ("Volatility", "Volatilité"), "structured": ("Structured Products", "Produits structurés"),
 "repo": ("Repo", "Repo"), "lending": ("Securities Lending", "Prêt de titres"), "collateral": ("Collateral & Margin", "Collatéral & Marge"),
 "option.select": ("Book option", "Option du portefeuille"), "option.none": ("Select the Equity Options demo book or add an option in Risk Lab.", "Choisissez la démo Options actions ou ajoutez une option dans Risque."),
 "option.price": ("Theoretical price", "Prix théorique"), "option.type": ("Option type", "Type d’option"), "strike": ("Strike", "Strike"), "maturity": ("Maturity (years)", "Maturité (années)"),
 "option.method": ("European BSM. Continuous rates and dividend yields; volatility in annual decimal units. Vega and Rho per percentage point; Theta per calendar day. No smile or liquidity model.", "BSM européen. Taux et dividendes continus ; volatilité annuelle décimale. Vega et Rho par point de pourcentage ; Theta par jour calendaire. Sans smile ni liquidité."),
 "financing.none": ("Select a bond as collateral and set the shared repo terms below.", "Sélectionnez une obligation en collatéral et les conditions du repo ci-dessous."),
 "financing.cash": ("Repo cash liability", "Dette de financement repo"), "financing.rate": ("Repo rate (%)", "Taux repo (%)"), "financing.haircut": ("Contractual haircut (%)", "Décote contractuelle (%)"), "financing.days": ("Tenor (days)", "Durée (jours)"),
 "financing.cost": ("Funding interest", "Intérêts de financement"), "financing.margin": ("Cash-equivalent margin", "Marge en équivalent cash"),
 "financing.method": ("Repo interest is simple ACT/360. Repo cash is a liability deducted from NAV; record its cash proceeds as a cash position. Contractual margin uses the original haircut. Refinancing haircut stress is separate from economic P&L.", "Intérêt repo simple ACT/360. La dette repo est déduite de la VL ; comptabilisez les fonds reçus en position cash. La marge contractuelle utilise la décote initiale. Le stress de refinancement est distinct du P&L économique."),
}
TRANSLATIONS = {lang: {key: pair[i] for key, pair in STRINGS.items()} for i, lang in enumerate(("en", "fr"))}

def t(key, lang=None, **values):
    if lang is None:
        from core.state import get_state
        lang = get_state().ui.language
    return TRANSLATIONS[lang][key].format(**values)

def error_message(exc):
    return t(str(exc)) if str(exc) in STRINGS else t("error")
