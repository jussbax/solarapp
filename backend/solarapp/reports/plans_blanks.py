"""The blank lines of the plan set (round 13 review, finding 5): one collector every sheet module appends to whenever it
prints BLANK with a reason, so the last sheet lists every blank line of the set grouped by sheet, and the signing
engineer's own lines (the frame rating, "fed from", the demand load, the branch-circuit figures) under their own heading.

A sheet module writes `blanks.add(SHEET, "the figure", "the reason, and where to type it")` where it prints the line:
`add` returns BLANK, so it stands in an f-string where BLANK stood. `n` counts the lines one entry stands for (a figure
printed in several cells of one table). The title block's signature line ("Signature ____ Date ____ Seal") is not a
figure and is never recorded; the signing engineer's profile fields print on every sheet and are listed once, by the
cover's own entry. Nothing is derived here: the modules compose the reasons, the collector only keeps them."""
from __future__ import annotations

BLANK = "__________"                        # a figure the app does not hold: a line for the signing engineer, never a guess


class Blanks:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, sheet: str, item: str, reason: str, *, engineer: bool = False, n: int = 1) -> str:
        """Records `n` blank lines on `sheet` for `item` with their `reason` (`engineer`: a line that is the signing engineer's
        to fill by design, not a figure the app lacks) and returns BLANK."""
        self.rows.append({"sheet": sheet, "item": item, "reason": reason, "engineer": bool(engineer), "n": max(int(n), 1)})
        return BLANK

    def count(self, sheet: str) -> int:
        return sum(r["n"] for r in self.rows if r["sheet"] == sheet)

    def grouped(self, sheet_names: list[str]) -> list[dict]:
        """One row per sheet and reason, in the set's order then in the order the lines were printed:
        {"sheet", "no" (1-based, None for a name not in the set), "engineer", "reason", "items": {item: n}, "n"}."""
        order = {name: i + 1 for i, name in enumerate(sheet_names)}
        groups: dict[tuple, dict] = {}
        for r in self.rows:
            key = (r["sheet"], r["engineer"], r["reason"])
            g = groups.setdefault(key, {"sheet": r["sheet"], "no": order.get(r["sheet"]), "engineer": r["engineer"], "reason": r["reason"], "items": {}, "n": 0})
            g["items"][r["item"]] = g["items"].get(r["item"], 0) + r["n"]
            g["n"] += r["n"]
        keys = list(groups)
        return sorted(groups.values(), key=lambda g: (g["no"] if g["no"] is not None else 10 ** 6, keys.index((g["sheet"], g["engineer"], g["reason"]))))
