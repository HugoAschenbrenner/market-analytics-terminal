"""
Repo Engine.

This module implements transparent repo cashflow and collateral margin analytics.

Financial conventions:
- Haircut is stored as a decimal, e.g. 2% = 0.02.
- Repo rate is stored as a decimal annualized rate, e.g. 4% = 0.04.
- Default day-count basis is ACT/360.
- Cash amount = collateral market value * (1 - haircut).
- Repo interest = cash amount * repo rate * repo days / day-count basis.
- Repurchase amount = cash amount + repo interest.
- Adjusted collateral value = collateral market value * (1 + collateral price shock).
- Eligible collateral = adjusted collateral value * (1 - haircut).
- Margin deficit = max(0, cash amount - eligible collateral).
- Margin surplus = max(0, eligible collateral - cash amount).

Important limitation:
This is a simplified repo cashflow and margin analytics model for demonstration.
It is not a legal, settlement, collateral management, counterparty risk, or close-out system.
"""

from __future__ import annotations

import math

from dataclasses import asdict, dataclass
from datetime import date
from typing import Union

import pandas as pd


DateLike = Union[str, date, pd.Timestamp]


@dataclass(frozen=True)
class RepoTradeResult:
    """Repo trade cashflow result."""

    collateral_market_value: float
    haircut: float
    cash_amount: float
    repo_rate: float
    start_date: date
    end_date: date
    repo_days: int
    day_count_basis: int
    repo_interest: float
    repurchase_amount: float
    currency: str


@dataclass(frozen=True)
class RepoMarginResult:
    """Repo margin and collateral stress result."""

    collateral_market_value: float
    cash_amount: float
    collateral_price_shock: float
    original_haircut: float
    new_haircut: float
    adjusted_collateral_value: float
    original_eligible_collateral: float
    new_eligible_collateral: float
    margin_deficit: float
    margin_surplus: float
    margin_call_required: bool
    deficit_pct_of_original_collateral: float
    driver: str


@dataclass(frozen=True)
class ContractualRepoMarginResult:
    """Contractual variation-margin result for an existing repo."""
    transaction_direction: str
    currency: str
    netting_set_id: str
    start_date: date
    end_date: date
    margin_date: date
    elapsed_days: int
    day_count_basis: int
    cash_amount: float
    repo_rate: float
    accrued_repo_interest_to_margin_date: float
    accrued_repurchase_price: float
    current_dirty_collateral_value: float
    contractual_haircut: float
    current_eligible_collateral: float
    cash_lender_exposure_gap: float
    threshold: float
    minimum_transfer_amount: float
    rounding_increment: float
    rounding_method: str
    threshold_adjusted_gap: float
    contractual_margin_transfer: float
    collateral_transfer_amount: float
    margin_transfer_required: bool
    transfer_direction: str
    contractual_haircut_reset_applied: bool
    model_status: str


@dataclass(frozen=True)
class RepoRefinancingStressResult:
    """Refinancing/re-roll haircut and liquidity stress result."""
    currency: str
    current_dirty_collateral_value: float
    collateral_price_shock: float
    shocked_dirty_collateral_value: float
    contractual_haircut: float
    refinancing_haircut: float
    current_funding_capacity: float
    price_shocked_capacity_at_contractual_haircut: float
    stressed_refinancing_funding_capacity: float
    collateral_price_liquidity_change: float
    haircut_reset_liquidity_change: float
    total_liquidity_change: float
    refinancing_liquidity_shortfall: float
    refinancing_liquidity_surplus: float
    is_contractual_variation_margin: bool
    driver: str
    model_status: str


def _to_date(value: DateLike) -> date:
    """Convert a date-like value to a Python date."""

    if isinstance(value, date):
        return value

    return pd.to_datetime(value).date()


def validate_repo_inputs(
    collateral_market_value: float,
    haircut: float,
    repo_rate: float,
    day_count_basis: int,
) -> None:
    """Validate core repo inputs."""

    if collateral_market_value <= 0:
        raise ValueError("Collateral market value must be positive.")

    if haircut < 0 or haircut >= 1:
        raise ValueError("Haircut must be between 0 and 1.")

    if day_count_basis <= 0:
        raise ValueError("Day-count basis must be positive.")

    # Negative repo rates can exist in some markets, so we do not reject them.
    if repo_rate < -0.10:
        raise ValueError("Repo rate is unrealistically negative for this simplified model.")


def validate_margin_inputs(
    collateral_market_value: float,
    cash_amount: float,
    original_haircut: float,
    new_haircut: float,
) -> None:
    """Validate margin analytics inputs."""

    if collateral_market_value <= 0:
        raise ValueError("Collateral market value must be positive.")

    if cash_amount < 0:
        raise ValueError("Cash amount cannot be negative.")

    if original_haircut < 0 or original_haircut >= 1:
        raise ValueError("Original haircut must be between 0 and 1.")

    if new_haircut < 0 or new_haircut >= 1:
        raise ValueError("New haircut must be between 0 and 1.")


def calculate_repo_days(start_date: DateLike, end_date: DateLike) -> int:
    """Calculate repo term in calendar days."""

    start = _to_date(start_date)
    end = _to_date(end_date)

    days = (end - start).days

    if days <= 0:
        raise ValueError("End date must be after start date.")

    return days


def calculate_cash_amount(
    collateral_market_value: float,
    haircut: float,
) -> float:
    """Calculate cash amount lent/borrowed against collateral.

    Formula:
    cash_amount = collateral_market_value * (1 - haircut)
    """

    return float(collateral_market_value * (1.0 - haircut))


def calculate_repo_interest(
    cash_amount: float,
    repo_rate: float,
    repo_days: int,
    day_count_basis: int = 360,
) -> float:
    """Calculate repo interest.

    Formula:
    repo_interest = cash_amount * repo_rate * repo_days / day_count_basis
    """

    return float(cash_amount * repo_rate * repo_days / day_count_basis)


def calculate_repurchase_amount(
    cash_amount: float,
    repo_interest: float,
) -> float:
    """Calculate repurchase amount at repo maturity."""

    return float(cash_amount + repo_interest)


def calculate_repo_trade(
    collateral_market_value: float,
    haircut: float,
    repo_rate: float,
    start_date: DateLike,
    end_date: DateLike,
    day_count_basis: int = 360,
    currency: str = "EUR",
) -> RepoTradeResult:
    """Calculate simplified repo trade cashflows."""

    validate_repo_inputs(
        collateral_market_value=collateral_market_value,
        haircut=haircut,
        repo_rate=repo_rate,
        day_count_basis=day_count_basis,
    )

    start = _to_date(start_date)
    end = _to_date(end_date)
    repo_days = calculate_repo_days(start, end)

    cash_amount = calculate_cash_amount(
        collateral_market_value=collateral_market_value,
        haircut=haircut,
    )

    repo_interest = calculate_repo_interest(
        cash_amount=cash_amount,
        repo_rate=repo_rate,
        repo_days=repo_days,
        day_count_basis=day_count_basis,
    )

    repurchase_amount = calculate_repurchase_amount(
        cash_amount=cash_amount,
        repo_interest=repo_interest,
    )

    return RepoTradeResult(
        collateral_market_value=float(collateral_market_value),
        haircut=float(haircut),
        cash_amount=float(cash_amount),
        repo_rate=float(repo_rate),
        start_date=start,
        end_date=end,
        repo_days=int(repo_days),
        day_count_basis=int(day_count_basis),
        repo_interest=float(repo_interest),
        repurchase_amount=float(repurchase_amount),
        currency=currency,
    )


def repo_result_to_dict(result: RepoTradeResult) -> dict:
    """Convert RepoTradeResult to dictionary for display/export."""

    output = asdict(result)
    output["start_date"] = result.start_date.isoformat()
    output["end_date"] = result.end_date.isoformat()
    return output


def calculate_repo_sensitivity_table(
    collateral_market_value: float,
    haircut: float,
    repo_rate: float,
    start_date: DateLike,
    end_date: DateLike,
    day_count_basis: int = 360,
    currency: str = "EUR",
) -> pd.DataFrame:
    """Generate a simple repo sensitivity table for haircut and repo rate."""

    scenarios = [
        {
            "scenario": "Base case",
            "haircut": haircut,
            "repo_rate": repo_rate,
        },
        {
            "scenario": "Haircut +2 percentage points",
            "haircut": min(haircut + 0.02, 0.99),
            "repo_rate": repo_rate,
        },
        {
            "scenario": "Haircut +5 percentage points",
            "haircut": min(haircut + 0.05, 0.99),
            "repo_rate": repo_rate,
        },
        {
            "scenario": "Repo rate +50 bps",
            "haircut": haircut,
            "repo_rate": repo_rate + 0.0050,
        },
        {
            "scenario": "Repo rate -50 bps",
            "haircut": haircut,
            "repo_rate": repo_rate - 0.0050,
        },
    ]

    rows = []

    for scenario in scenarios:
        result = calculate_repo_trade(
            collateral_market_value=collateral_market_value,
            haircut=scenario["haircut"],
            repo_rate=scenario["repo_rate"],
            start_date=start_date,
            end_date=end_date,
            day_count_basis=day_count_basis,
            currency=currency,
        )

        rows.append(
            {
                "scenario": scenario["scenario"],
                "haircut": result.haircut,
                "repo_rate": result.repo_rate,
                "cash_amount": result.cash_amount,
                "repo_interest": result.repo_interest,
                "repurchase_amount": result.repurchase_amount,
            }
        )

    return pd.DataFrame(rows)


def calculate_adjusted_collateral_value(
    collateral_market_value: float,
    collateral_price_shock: float,
) -> float:
    """Calculate collateral value after price shock.

    Formula:
    adjusted_collateral_value = collateral_market_value * (1 + collateral_price_shock)
    """

    return float(collateral_market_value * (1.0 + collateral_price_shock))


def calculate_eligible_collateral(
    collateral_market_value: float,
    haircut: float,
) -> float:
    """Calculate eligible collateral after haircut.

    Formula:
    eligible_collateral = collateral_market_value * (1 - haircut)
    """

    return float(collateral_market_value * (1.0 - haircut))


def identify_margin_driver(
    collateral_price_shock: float,
    original_haircut: float,
    new_haircut: float,
) -> str:
    """Identify the main driver of a margin change."""

    haircut_increase = new_haircut > original_haircut
    collateral_drop = collateral_price_shock < 0

    if collateral_drop and haircut_increase:
        return "Collateral depreciation and haircut increase"

    if collateral_drop:
        return "Collateral depreciation"

    if haircut_increase:
        return "Haircut increase"

    if collateral_price_shock > 0 and new_haircut <= original_haircut:
        return "Collateral appreciation / no adverse haircut change"

    return "No adverse margin driver"


SUPPORTED_REPO_DIRECTIONS = (
    "Cash lender / reverse repo",
    "Cash borrower / repo",
)

SUPPORTED_MARGIN_ROUNDING_METHODS = (
    "Nearest",
    "Away from zero",
    "None",
)


def _validate_non_negative_amount(value: float, field_name: str) -> float:
    resolved = float(value)
    if not math.isfinite(resolved) or resolved < 0:
        raise ValueError(f"{field_name} must be finite and non-negative.")
    return resolved


def _validate_repo_direction(transaction_direction: str) -> str:
    direction = str(transaction_direction).strip()
    if direction not in SUPPORTED_REPO_DIRECTIONS:
        raise ValueError(
            "Unsupported repo direction. Choose one of "
            f"{SUPPORTED_REPO_DIRECTIONS}."
        )
    return direction


def _validate_rounding_method(rounding_method: str) -> str:
    method = str(rounding_method).strip()
    if method not in SUPPORTED_MARGIN_ROUNDING_METHODS:
        raise ValueError(
            "Unsupported margin rounding method. Choose one of "
            f"{SUPPORTED_MARGIN_ROUNDING_METHODS}."
        )
    return method


def _round_signed_margin_transfer(
    amount: float,
    rounding_increment: float,
    rounding_method: str,
) -> float:
    method = _validate_rounding_method(rounding_method)
    increment = _validate_non_negative_amount(
        rounding_increment,
        "Rounding increment",
    )
    resolved_amount = float(amount)
    if not math.isfinite(resolved_amount):
        raise ValueError("Margin transfer amount must be finite.")
    if method == "None" or increment == 0:
        return resolved_amount
    sign = 1.0 if resolved_amount >= 0 else -1.0
    units = abs(resolved_amount) / increment
    rounded_units = (
        math.floor(units + 0.5)
        if method == "Nearest"
        else math.ceil(units)
    )
    return float(sign * rounded_units * increment)


def calculate_accrued_repurchase_price(
    cash_amount: float,
    repo_rate: float,
    start_date: DateLike,
    margin_date: DateLike,
    day_count_basis: int = 360,
    end_date: DateLike | None = None,
) -> tuple[int, float, float]:
    """Accrue the repo cash exposure to the contractual margin date."""
    cash = _validate_non_negative_amount(cash_amount, "Cash amount")
    if day_count_basis <= 0:
        raise ValueError("Day-count basis must be positive.")
    start = _to_date(start_date)
    margin = _to_date(margin_date)
    if margin < start:
        raise ValueError("Margin date cannot precede repo start date.")
    if end_date is not None:
        end = _to_date(end_date)
        if end <= start:
            raise ValueError("Repo end date must be after start date.")
        if margin > end:
            raise ValueError("Margin date cannot be after repo end date.")
    elapsed_days = (margin - start).days
    accrued_interest = calculate_repo_interest(
        cash_amount=cash,
        repo_rate=float(repo_rate),
        repo_days=elapsed_days,
        day_count_basis=int(day_count_basis),
    )
    accrued_repurchase_price = cash + accrued_interest
    if accrued_repurchase_price < 0:
        raise ValueError("Accrued repurchase price cannot be negative.")
    return int(elapsed_days), float(accrued_interest), float(accrued_repurchase_price)


def calculate_contractual_variation_margin(
    cash_amount: float,
    repo_rate: float,
    start_date: DateLike,
    end_date: DateLike,
    margin_date: DateLike,
    day_count_basis: int,
    current_dirty_collateral_value: float,
    contractual_haircut: float,
    transaction_direction: str,
    threshold: float = 0.0,
    minimum_transfer_amount: float = 0.0,
    rounding_increment: float = 1.0,
    rounding_method: str = "Nearest",
    currency: str = "EUR",
    netting_set_id: str = "NS-1",
) -> ContractualRepoMarginResult:
    """
    Calculate contractual variation margin for the existing repo.

    The contractual haircut is held fixed. A refinancing/re-roll
    haircut is deliberately excluded from this calculation.
    """
    direction = _validate_repo_direction(transaction_direction)
    method = _validate_rounding_method(rounding_method)
    cash = _validate_non_negative_amount(cash_amount, "Cash amount")
    dirty_collateral = _validate_non_negative_amount(
        current_dirty_collateral_value,
        "Current dirty collateral value",
    )
    resolved_threshold = _validate_non_negative_amount(threshold, "Threshold")
    resolved_mta = _validate_non_negative_amount(
        minimum_transfer_amount,
        "Minimum transfer amount",
    )
    resolved_rounding = _validate_non_negative_amount(
        rounding_increment,
        "Rounding increment",
    )
    if contractual_haircut < 0 or contractual_haircut >= 1:
        raise ValueError("Contractual haircut must be between 0 and 1.")
    resolved_currency = str(currency).strip().upper()
    if not resolved_currency:
        raise ValueError("Currency cannot be blank.")
    resolved_netting_set = str(netting_set_id).strip()
    if not resolved_netting_set:
        raise ValueError("Netting-set ID cannot be blank.")
    start = _to_date(start_date)
    end = _to_date(end_date)
    margin = _to_date(margin_date)
    elapsed_days, accrued_interest, accrued_repurchase_price = (
        calculate_accrued_repurchase_price(
            cash_amount=cash,
            repo_rate=float(repo_rate),
            start_date=start,
            margin_date=margin,
            day_count_basis=int(day_count_basis),
            end_date=end,
        )
    )
    eligible_collateral = calculate_eligible_collateral(
        collateral_market_value=dirty_collateral,
        haircut=float(contractual_haircut),
    )
    # Positive means the cash lender is under-collateralized.
    gross_gap = accrued_repurchase_price - eligible_collateral
    if abs(gross_gap) <= resolved_threshold:
        threshold_adjusted_gap = 0.0
    else:
        threshold_adjusted_gap = math.copysign(
            abs(gross_gap) - resolved_threshold,
            gross_gap,
        )
    if abs(threshold_adjusted_gap) < resolved_mta:
        executable_transfer = 0.0
    else:
        executable_transfer = _round_signed_margin_transfer(
            amount=threshold_adjusted_gap,
            rounding_increment=resolved_rounding,
            rounding_method=method,
        )
    transfer_required = abs(executable_transfer) > 0
    if not transfer_required:
        transfer_direction = "No contractual margin transfer"
    elif executable_transfer > 0:
        transfer_direction = (
            "Cash lender receives additional collateral"
            if direction == "Cash lender / reverse repo"
            else "Cash borrower posts additional collateral"
        )
    else:
        transfer_direction = (
            "Cash lender returns excess collateral"
            if direction == "Cash lender / reverse repo"
            else "Cash borrower receives collateral back"
        )
    return ContractualRepoMarginResult(
        transaction_direction=direction,
        currency=resolved_currency,
        netting_set_id=resolved_netting_set,
        start_date=start,
        end_date=end,
        margin_date=margin,
        elapsed_days=int(elapsed_days),
        day_count_basis=int(day_count_basis),
        cash_amount=float(cash),
        repo_rate=float(repo_rate),
        accrued_repo_interest_to_margin_date=float(accrued_interest),
        accrued_repurchase_price=float(accrued_repurchase_price),
        current_dirty_collateral_value=float(dirty_collateral),
        contractual_haircut=float(contractual_haircut),
        current_eligible_collateral=float(eligible_collateral),
        cash_lender_exposure_gap=float(gross_gap),
        threshold=float(resolved_threshold),
        minimum_transfer_amount=float(resolved_mta),
        rounding_increment=float(resolved_rounding),
        rounding_method=method,
        threshold_adjusted_gap=float(threshold_adjusted_gap),
        contractual_margin_transfer=float(executable_transfer),
        collateral_transfer_amount=float(abs(executable_transfer)),
        margin_transfer_required=bool(transfer_required),
        transfer_direction=transfer_direction,
        contractual_haircut_reset_applied=False,
        model_status="Contractual variation-margin proxy",
    )


def contractual_margin_result_to_dict(
    result: ContractualRepoMarginResult,
) -> dict:
    output = asdict(result)
    output["start_date"] = result.start_date.isoformat()
    output["end_date"] = result.end_date.isoformat()
    output["margin_date"] = result.margin_date.isoformat()
    return output


def calculate_refinancing_haircut_stress(
    current_dirty_collateral_value: float,
    contractual_haircut: float,
    refinancing_haircut: float,
    collateral_price_shock: float = 0.0,
    currency: str = "EUR",
) -> RepoRefinancingStressResult:
    """Calculate refinancing/re-roll funding-capacity and liquidity stress."""
    current_dirty = _validate_non_negative_amount(
        current_dirty_collateral_value,
        "Current dirty collateral value",
    )
    for haircut_value, label in [
        (contractual_haircut, "Contractual haircut"),
        (refinancing_haircut, "Refinancing haircut"),
    ]:
        if haircut_value < 0 or haircut_value >= 1:
            raise ValueError(f"{label} must be between 0 and 1.")
    shock = float(collateral_price_shock)
    if not math.isfinite(shock) or shock <= -1:
        raise ValueError(
            "Collateral price shock must be finite and greater than -100%."
        )
    shocked_dirty = current_dirty * (1.0 + shock)
    current_capacity = calculate_eligible_collateral(
        collateral_market_value=current_dirty,
        haircut=float(contractual_haircut),
    )
    shocked_capacity_at_contractual_haircut = calculate_eligible_collateral(
        collateral_market_value=shocked_dirty,
        haircut=float(contractual_haircut),
    )
    stressed_capacity = calculate_eligible_collateral(
        collateral_market_value=shocked_dirty,
        haircut=float(refinancing_haircut),
    )
    price_change = shocked_capacity_at_contractual_haircut - current_capacity
    haircut_change = stressed_capacity - shocked_capacity_at_contractual_haircut
    total_change = stressed_capacity - current_capacity
    shortfall = max(0.0, -total_change)
    surplus = max(0.0, total_change)
    adverse_price = shock < 0
    adverse_haircut = refinancing_haircut > contractual_haircut
    if adverse_price and adverse_haircut:
        driver = "Collateral depreciation and refinancing haircut reset"
    elif adverse_price:
        driver = "Collateral depreciation"
    elif adverse_haircut:
        driver = "Refinancing haircut reset"
    elif total_change > 0:
        driver = "Improved refinancing capacity"
    else:
        driver = "No adverse refinancing driver"
    return RepoRefinancingStressResult(
        currency=str(currency).strip().upper(),
        current_dirty_collateral_value=float(current_dirty),
        collateral_price_shock=shock,
        shocked_dirty_collateral_value=float(shocked_dirty),
        contractual_haircut=float(contractual_haircut),
        refinancing_haircut=float(refinancing_haircut),
        current_funding_capacity=float(current_capacity),
        price_shocked_capacity_at_contractual_haircut=float(
            shocked_capacity_at_contractual_haircut
        ),
        stressed_refinancing_funding_capacity=float(stressed_capacity),
        collateral_price_liquidity_change=float(price_change),
        haircut_reset_liquidity_change=float(haircut_change),
        total_liquidity_change=float(total_change),
        refinancing_liquidity_shortfall=float(shortfall),
        refinancing_liquidity_surplus=float(surplus),
        is_contractual_variation_margin=False,
        driver=driver,
        model_status="Refinancing/re-roll liquidity stress",
    )


def refinancing_stress_result_to_dict(
    result: RepoRefinancingStressResult,
) -> dict:
    return asdict(result)


def calculate_refinancing_stress_table(
    current_dirty_collateral_value: float,
    contractual_haircut: float,
    currency: str = "EUR",
) -> pd.DataFrame:
    scenarios = [
        {
            "scenario": "Base refinancing capacity",
            "collateral_price_shock": 0.00,
            "refinancing_haircut": contractual_haircut,
        },
        {
            "scenario": "Collateral -3%, contractual haircut retained",
            "collateral_price_shock": -0.03,
            "refinancing_haircut": contractual_haircut,
        },
        {
            "scenario": "Collateral unchanged, refinancing haircut +2pp",
            "collateral_price_shock": 0.00,
            "refinancing_haircut": min(contractual_haircut + 0.02, 0.99),
        },
        {
            "scenario": "Collateral -5%, refinancing haircut +2pp",
            "collateral_price_shock": -0.05,
            "refinancing_haircut": min(contractual_haircut + 0.02, 0.99),
        },
        {
            "scenario": "Collateral -10%, refinancing haircut +5pp",
            "collateral_price_shock": -0.10,
            "refinancing_haircut": min(contractual_haircut + 0.05, 0.99),
        },
    ]
    rows = []
    for scenario in scenarios:
        result = calculate_refinancing_haircut_stress(
            current_dirty_collateral_value=current_dirty_collateral_value,
            contractual_haircut=contractual_haircut,
            refinancing_haircut=scenario["refinancing_haircut"],
            collateral_price_shock=scenario["collateral_price_shock"],
            currency=currency,
        )
        row = refinancing_stress_result_to_dict(result)
        row["scenario"] = scenario["scenario"]
        rows.append(row)
    return pd.DataFrame(rows)


def generate_contractual_margin_commentary(
    result: ContractualRepoMarginResult,
) -> list[str]:
    comments = [
        (
            f"Margin date {result.margin_date.isoformat()}: the accrued "
            f"repurchase price is {result.accrued_repurchase_price:,.0f} "
            f"after {result.elapsed_days} accrued day(s)."
        ),
        (
            f"The contractual haircut remains fixed at "
            f"{result.contractual_haircut:.2%}; no haircut reset enters "
            "contractual variation margin."
        ),
        (
            f"Current dirty collateral value is "
            f"{result.current_dirty_collateral_value:,.0f}; eligible "
            f"collateral is {result.current_eligible_collateral:,.0f}."
        ),
    ]
    if result.margin_transfer_required:
        comments.append(
            f"{result.transfer_direction}: "
            f"{result.collateral_transfer_amount:,.0f} after threshold, "
            f"MTA and {result.rounding_method.lower()} rounding."
        )
    else:
        comments.append(
            "No contractual margin transfer is executable after threshold, "
            "MTA and rounding."
        )
    comments.append(
        "Any stressed haircut is reported separately as a refinancing/re-roll "
        "liquidity stress, not as a margin call on the existing repo."
    )
    comments.append(
        "This remains a single-currency, single-netting-set proxy and does not "
        "implement full GMRA netting, dispute mechanics, settlement timing or "
        "legal close-out."
    )
    return comments


def calculate_margin_call(
    collateral_market_value: float,
    cash_amount: float,
    original_haircut: float,
    collateral_price_shock: float,
    new_haircut: float,
) -> RepoMarginResult:
    """Calculate margin deficit or surplus after collateral and haircut shocks."""

    validate_margin_inputs(
        collateral_market_value=collateral_market_value,
        cash_amount=cash_amount,
        original_haircut=original_haircut,
        new_haircut=new_haircut,
    )

    adjusted_collateral_value = calculate_adjusted_collateral_value(
        collateral_market_value=collateral_market_value,
        collateral_price_shock=collateral_price_shock,
    )

    original_eligible_collateral = calculate_eligible_collateral(
        collateral_market_value=collateral_market_value,
        haircut=original_haircut,
    )

    new_eligible_collateral = calculate_eligible_collateral(
        collateral_market_value=adjusted_collateral_value,
        haircut=new_haircut,
    )

    margin_deficit = max(0.0, cash_amount - new_eligible_collateral)
    margin_surplus = max(0.0, new_eligible_collateral - cash_amount)
    margin_call_required = margin_deficit > 0.0

    deficit_pct_of_original_collateral = margin_deficit / collateral_market_value

    driver = identify_margin_driver(
        collateral_price_shock=collateral_price_shock,
        original_haircut=original_haircut,
        new_haircut=new_haircut,
    )

    return RepoMarginResult(
        collateral_market_value=float(collateral_market_value),
        cash_amount=float(cash_amount),
        collateral_price_shock=float(collateral_price_shock),
        original_haircut=float(original_haircut),
        new_haircut=float(new_haircut),
        adjusted_collateral_value=float(adjusted_collateral_value),
        original_eligible_collateral=float(original_eligible_collateral),
        new_eligible_collateral=float(new_eligible_collateral),
        margin_deficit=float(margin_deficit),
        margin_surplus=float(margin_surplus),
        margin_call_required=bool(margin_call_required),
        deficit_pct_of_original_collateral=float(deficit_pct_of_original_collateral),
        driver=driver,
    )


def margin_result_to_dict(result: RepoMarginResult) -> dict:
    """Convert RepoMarginResult to dictionary for display/export."""

    return asdict(result)


def calculate_margin_stress_table(
    collateral_market_value: float,
    cash_amount: float,
    original_haircut: float,
) -> pd.DataFrame:
    """Generate predefined collateral and haircut stress scenarios."""

    scenarios = [
        {
            "scenario": "Base case",
            "collateral_price_shock": 0.00,
            "new_haircut": original_haircut,
        },
        {
            "scenario": "Collateral -3%, haircut unchanged",
            "collateral_price_shock": -0.03,
            "new_haircut": original_haircut,
        },
        {
            "scenario": "Collateral -5%, haircut +2pp",
            "collateral_price_shock": -0.05,
            "new_haircut": min(original_haircut + 0.02, 0.99),
        },
        {
            "scenario": "Collateral -10%, haircut +5pp",
            "collateral_price_shock": -0.10,
            "new_haircut": min(original_haircut + 0.05, 0.99),
        },
        {
            "scenario": "Collateral +3%, haircut unchanged",
            "collateral_price_shock": 0.03,
            "new_haircut": original_haircut,
        },
    ]

    rows = []

    for scenario in scenarios:
        result = calculate_margin_call(
            collateral_market_value=collateral_market_value,
            cash_amount=cash_amount,
            original_haircut=original_haircut,
            collateral_price_shock=scenario["collateral_price_shock"],
            new_haircut=scenario["new_haircut"],
        )

        rows.append(
            {
                "scenario": scenario["scenario"],
                "collateral_price_shock": result.collateral_price_shock,
                "original_haircut": result.original_haircut,
                "new_haircut": result.new_haircut,
                "adjusted_collateral_value": result.adjusted_collateral_value,
                "new_eligible_collateral": result.new_eligible_collateral,
                "margin_deficit": result.margin_deficit,
                "margin_surplus": result.margin_surplus,
                "margin_call_required": result.margin_call_required,
                "deficit_pct_of_original_collateral": result.deficit_pct_of_original_collateral,
                "driver": result.driver,
            }
        )

    return pd.DataFrame(rows)


def generate_repo_margin_commentary(result: RepoMarginResult) -> list[str]:
    """Generate desk-style repo margin commentary."""

    comments = []

    if result.margin_call_required:
        comments.append(
            f"Margin call required: deficit of {result.margin_deficit:,.0f}, "
            f"equal to {result.deficit_pct_of_original_collateral:.2%} of original collateral value."
        )
    else:
        comments.append(
            f"No margin call required. Eligible collateral exceeds cash amount by {result.margin_surplus:,.0f}."
        )

    comments.append(f"Main driver: {result.driver}.")

    if result.new_haircut > result.original_haircut:
        comments.append(
            f"Haircut increased from {result.original_haircut:.2%} to {result.new_haircut:.2%}, "
            "reducing eligible collateral."
        )

    if result.collateral_price_shock < 0:
        comments.append(
            f"Collateral value fell by {abs(result.collateral_price_shock):.2%}, directly reducing the collateral base."
        )

    comments.append(
        "This is a simplified collateral analytics proxy and does not model legal close-out, settlement timing, or counterparty default."
    )

    return comments
