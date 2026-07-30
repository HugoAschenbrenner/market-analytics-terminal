from pathlib import Path


def test_interactive_options_greeks_lab_is_rendered_after_black_scholes():
    page = Path("app_pages/structured_products.py").read_text()

    assert "def _render_interactive_options_greeks_lab() -> None:" in page
    assert 'st.subheader("Interactive Greeks & Sensitivity Explorer")' in page
    assert "_render_black_scholes_pricer_lab()" in page
    assert "_render_interactive_options_greeks_lab()" in page
    assert page.index("_render_black_scholes_pricer_lab()") < page.index(
        "_render_interactive_options_greeks_lab()"
    )


def test_interactive_options_greeks_lab_uses_curve_engine():
    page = Path("app_pages/structured_products.py").read_text()

    assert "build_bsm_interactive_explorer_payload" in page
    assert "build_local_tangent_line" in page
    assert "Theoretical Value Curve and Local Tangent" in page
    assert "Greeks Across Selected Shock Axis" in page
    assert "Desk interpretation" in page


def test_interactive_options_greeks_lab_has_no_unsafe_snapshot_price_access():
    page = Path("app_pages/structured_products.py").read_text()

    assert "interactive_theoretical_value = float(" in page
    assert "snapshot['price']" not in page
    assert 'snapshot["price"]' not in page
    assert "interactive_delta" in page
    assert "interactive_vega_1pct" in page


def test_interactive_options_greeks_lab_anchor_point_has_no_duplicate_column_rename():
    page = Path("app_pages/structured_products.py").read_text()

    assert "anchor_df = pd.DataFrame" in page
    assert "alt.Chart(anchor_df)" in page
    assert "tangent.rename(" not in page
    assert "anchor_x" in page
    assert "anchor_y" in page


def test_interactive_options_greeks_metric_cards_use_selected_curve_anchor():
    page = Path("app_pages/structured_products.py").read_text()

    assert "anchor_row = selected_curve.loc[anchor_idx]" in page
    assert 'interactive_theoretical_value = float(anchor_row["price"])' in page
    assert 'interactive_delta = float(anchor_row["delta"])' in page
    assert "selected_x=selected_axis_value" in page
