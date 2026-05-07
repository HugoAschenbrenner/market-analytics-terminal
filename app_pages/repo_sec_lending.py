from app_pages.common import (
    render_module_header,
    render_planned_outputs,
    render_validation_box,
    render_status_badge,
)


def render() -> None:
    render_module_header(
        title="Repo & Securities Lending",
        caption="Funding, collateral, haircut, margin call, and borrow fee analytics.",
        objective=(
            "Objective: explain how repo and securities lending trades are affected by funding costs, "
            "haircuts, collateral moves, borrow fees, and margin requirements."
        ),
    )

    render_status_badge("Planned — second desk utility module")

    render_planned_outputs(
        [
            "Repo cash amount",
            "Repo interest",
            "Repurchase amount",
            "Haircut impact",
            "Collateral price shock",
            "New eligible collateral",
            "Margin deficit or surplus",
            "Margin call indicator",
            "Securities lending borrow fee",
            "Rebate and collateralization",
            "Specialness indicator",
            "Financing and margin Excel report",
        ]
    )

    render_validation_box(
        [
            "Higher haircut must reduce cash available against the same collateral.",
            "Higher repo rate must increase the repurchase amount.",
            "Collateral price drop must increase or maintain the margin deficit.",
            "Haircut increase must increase or maintain the margin deficit.",
            "Borrow fee and rebate conventions must be clearly stated.",
        ]
    )
