import os
import json
from typing import Optional, Dict
from models import CompetitorSnapshot, DiffReport, PriceDelta

class DiffEngine:
    """
    Compares the newly scraped snapshot against previous historical snapshots to detect pricing changes.
    """
    def __init__(self, snapshots_dir: str = "./data/snapshots"):
        self.snapshots_dir = snapshots_dir
        os.makedirs(self.snapshots_dir, exist_ok=True)

    def get_snapshot_path(self, competitor_id: str) -> str:
        return os.path.join(self.snapshots_dir, f"{competitor_id}_latest.json")

    def load_previous_snapshot(self, competitor_id: str) -> Optional[CompetitorSnapshot]:
        path = self.get_snapshot_path(competitor_id)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return CompetitorSnapshot(**data)
            except Exception:
                return None
        return None

    def save_snapshot(self, snapshot: CompetitorSnapshot):
        path = self.get_snapshot_path(snapshot.competitor_id)
        with open(path, "w", encoding="utf-8") as f:
            f.write(snapshot.model_dump_json(indent=2))

    def compute_diff(self, current: CompetitorSnapshot, previous: Optional[CompetitorSnapshot] = None, threshold_pct: float = 0.0) -> DiffReport:
        report = DiffReport(
            competitor_id=current.competitor_id,
            competitor_name=current.competitor_name,
            total_items_scanned=len(current.items)
        )

        if not previous or not previous.items:
            for item in current.items:
                report.new_items.append(PriceDelta(
                    competitor_id=current.competitor_id,
                    competitor_name=current.competitor_name,
                    item_name=item.name,
                    category=item.category,
                    old_price=None,
                    new_price=item.price,
                    currency=item.currency,
                    delta_amount=None,
                    delta_percentage=None,
                    change_type="NEW_ITEM"
                ))
            report.has_significant_change = True
            return report

        prev_dict: Dict[str, float] = {item.name.lower().strip(): item.price for item in previous.items}
        curr_dict: Dict[str, float] = {item.name.lower().strip(): item.price for item in current.items}

        for item in current.items:
            key = item.name.lower().strip()
            if key in prev_dict:
                old_p = prev_dict[key]
                new_p = item.price
                diff_amount = round(new_p - old_p, 2)
                diff_pct = round((diff_amount / old_p) * 100, 2) if old_p > 0 else 0.0

                if abs(diff_pct) >= threshold_pct and diff_amount != 0:
                    change_type = "PRICE_INCREASE" if diff_amount > 0 else "PRICE_DECREASE"
                    delta = PriceDelta(
                        competitor_id=current.competitor_id,
                        competitor_name=current.competitor_name,
                        item_name=item.name,
                        category=item.category,
                        old_price=old_p,
                        new_price=new_p,
                        currency=item.currency,
                        delta_amount=diff_amount,
                        delta_percentage=diff_pct,
                        change_type=change_type
                    )
                    if diff_amount > 0:
                        report.price_increases.append(delta)
                    else:
                        report.price_decreases.append(delta)
                else:
                    report.unchanged_items.append(PriceDelta(
                        competitor_id=current.competitor_id,
                        competitor_name=current.competitor_name,
                        item_name=item.name,
                        category=item.category,
                        old_price=old_p,
                        new_price=new_p,
                        currency=item.currency,
                        delta_amount=0.0,
                        delta_percentage=0.0,
                        change_type="UNCHANGED"
                    ))
            else:
                report.new_items.append(PriceDelta(
                    competitor_id=current.competitor_id,
                    competitor_name=current.competitor_name,
                    item_name=item.name,
                    category=item.category,
                    old_price=None,
                    new_price=item.price,
                    currency=item.currency,
                    delta_amount=None,
                    delta_percentage=None,
                    change_type="NEW_ITEM"
                ))

        for item in previous.items:
            key = item.name.lower().strip()
            if key not in curr_dict:
                report.discontinued_items.append(PriceDelta(
                    competitor_id=current.competitor_id,
                    competitor_name=current.competitor_name,
                    item_name=item.name,
                    category=item.category,
                    old_price=item.price,
                    new_price=None,
                    currency=item.currency,
                    delta_amount=None,
                    delta_percentage=None,
                    change_type="DISCONTINUED"
                ))

        report.has_significant_change = bool(report.price_increases or report.price_decreases or report.new_items or report.discontinued_items)
        return report
