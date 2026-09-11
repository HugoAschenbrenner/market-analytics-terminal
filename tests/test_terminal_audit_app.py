"""Execute Streamlit workflows, including interactions missed by source-text tests."""

import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest


@pytest.mark.parametrize("page", ["home", "fixed-income-risk", "repo-sec-lending",
                                  "structured-products", "portfolio-risk", "cross-asset-dashboard"])
def test_default_app_pages_render_without_errors(page):
    app = AppTest.from_file(str(Path("app.py").resolve()), default_timeout=40)
    app.query_params["page"] = page
    app.run()
    assert not app.exception
    assert not app.error
