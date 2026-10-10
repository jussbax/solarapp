# Datasheet fixture workbooks (round 12)

Three workbooks cut from the owner's files in `backend/datasheets/` on 10 October 2026, read by
`tests/test_datasheets_parse.py` and `tests/test_datasheets_match.py`. Every irregular cell of the brief's
section 1.5 and every sheet's layout are kept (the panel sheet starting at column O, the unlabelled LV/HV
column left of BATTERY TYPE, the Felicity inverter sheet's header on row 4, the Solis orphan rows with the
model text in the Details column, battery sheet 3's maker sub-headers with the blank rows between the blocks).
Nothing in a kept row was edited.

| File | Source | What was cut |
|---|---|---|
| `ALL_SOLAR_PANEL_DATA_SHEET.xlsx` | `backend/datasheets/ALL_SOLAR_PANEL_DATA_SHEET.xlsx`, 10 Oct 2026 | nothing: all 14 rows |
| `ALL_INVERTER_DATA_SHEET.xlsx` | `backend/datasheets/ALL_INVERTER_DATA_SHEET.xlsx`, 10 Oct 2026 | the plain 3P grid-tie rows that carry nothing the parser or the matcher needs: Deye sheet rows 8–14 (so the hybrids sit on rows 9–20) and Solis sheet rows 12–25 (the hybrids on rows 12–24, the orphan rows on 33–39) |
| `ALL_BATTERY_DATA_SHEET.xlsx` | `backend/datasheets/ALL_BATTERY_DATA_SHEET.xlsx`, 10 Oct 2026 | nothing: all 82 rows and the six sub-headers |

Rebuilt from the owner's files with `openpyxl` (`delete_rows` on the two sheets above); the row numbers the
tests quote are the fixture's.
