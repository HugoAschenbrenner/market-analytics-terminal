from engines.scenario_engine import (
    Scenario,
    describe_scenario,
    get_all_scenarios,
    get_credit_scenarios,
    get_equity_scenarios,
    get_fx_scenarios,
    get_rates_scenarios,
    get_repo_collateral_scenarios,
    get_volatility_scenarios,
    scenarios_to_records,
)


def test_get_all_scenarios_returns_non_empty_list():
    scenarios = get_all_scenarios()

    assert isinstance(scenarios, list)
    assert len(scenarios) > 0
    assert all(isinstance(scenario, Scenario) for scenario in scenarios)


def test_all_scenarios_have_required_fields():
    scenarios = get_all_scenarios()

    for scenario in scenarios:
        assert scenario.name
        assert scenario.risk_factor
        assert scenario.shock_type
        assert scenario.shock_value is not None
        assert scenario.unit
        assert scenario.description


def test_rates_bps_are_stored_as_decimal_rate_changes():
    scenarios = get_rates_scenarios()

    parallel_25 = next(
        scenario for scenario in scenarios if scenario.name == "+25 bps parallel rates shock"
    )
    parallel_50 = next(
        scenario for scenario in scenarios if scenario.name == "+50 bps parallel rates shock"
    )
    parallel_minus_25 = next(
        scenario for scenario in scenarios if scenario.name == "-25 bps parallel rates shock"
    )

    assert parallel_25.shock_value == 0.0025
    assert parallel_50.shock_value == 0.0050
    assert parallel_minus_25.shock_value == -0.0025


def test_credit_spread_bps_are_stored_as_decimal_spread_changes():
    scenarios = get_credit_scenarios()

    spread_50 = next(
        scenario for scenario in scenarios if scenario.name == "Credit spread +50 bps"
    )

    assert spread_50.shock_value == 0.0050
    assert spread_50.unit == "decimal_spread_change"


def test_equity_scenarios_are_decimal_returns():
    scenarios = get_equity_scenarios()

    spot_down_10 = next(
        scenario for scenario in scenarios if scenario.name == "Equity spot -10%"
    )

    assert spot_down_10.shock_value == -0.10
    assert spot_down_10.unit == "decimal_return"


def test_volatility_scenarios_are_absolute_vol_changes():
    scenarios = get_volatility_scenarios()

    vol_up_5 = next(
        scenario for scenario in scenarios if scenario.name == "Volatility +5 points"
    )

    assert vol_up_5.shock_value == 0.05
    assert vol_up_5.unit == "absolute_vol_change"


def test_fx_scenarios_are_decimal_returns():
    scenarios = get_fx_scenarios()

    usd_up = next(scenario for scenario in scenarios if scenario.name == "USD +2%")

    assert usd_up.shock_value == 0.02
    assert usd_up.unit == "decimal_return"


def test_repo_haircut_scenarios_are_absolute_decimal_changes():
    scenarios = get_repo_collateral_scenarios()

    haircut_up_2 = next(
        scenario for scenario in scenarios if scenario.name == "Haircut +2 percentage points"
    )

    assert haircut_up_2.shock_value == 0.02
    assert haircut_up_2.unit == "absolute_decimal_change"


def test_curve_scenarios_can_store_bucket_level_shocks():
    scenarios = get_rates_scenarios()

    steepener = next(scenario for scenario in scenarios if scenario.name == "2s10s steepener")

    assert isinstance(steepener.shock_value, dict)
    assert steepener.shock_value["10Y"] > steepener.shock_value["2Y"]


def test_describe_scenario_returns_non_empty_string():
    scenario = get_all_scenarios()[0]
    description = describe_scenario(scenario)

    assert isinstance(description, str)
    assert scenario.name in description
    assert scenario.risk_factor in description


def test_scenarios_to_records_returns_list_of_dicts():
    scenarios = get_all_scenarios()
    records = scenarios_to_records(scenarios)

    assert isinstance(records, list)
    assert isinstance(records[0], dict)
    assert "name" in records[0]
    assert "risk_factor" in records[0]
    assert "shock_type" in records[0]
    assert "shock_value" in records[0]
    assert "unit" in records[0]
    assert "description" in records[0]
