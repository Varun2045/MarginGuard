import os
from datetime import datetime
from typing import List
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from models import CompetitorSnapshot, PriceDelta, DiffReport

class ExcelManager:
    """
    Manages the competitor_price_tracker.xlsx workbook with formatted overview and change logs.
    """
    def __init__(self, excel_path: str = "./data/competitor_price_tracker.xlsx"):
        self.excel_path = excel_path
        os.makedirs(os.path.dirname(os.path.abspath(self.excel_path)), exist_ok=True)
        self._ensure_workbook_exists()

    def _ensure_workbook_exists(self):
        if not os.path.exists(self.excel_path):
            wb = openpyxl.Workbook()
            # Overview Sheet
            ws_overview = wb.active
            ws_overview.title = "Current Pricing Overview"
            self._apply_headers(ws_overview, [
                "Competitor Name", "Category", "Service / Product", "Current Price ($)", "Unit / Frequency", "Last Verified Date"
            ], "1E3A8A")

            # Change History Sheet
            ws_history = wb.create_sheet(title="Price Change History")
            self._apply_headers(ws_history, [
                "Timestamp", "Competitor", "Category", "Service / Item", "Old Price ($)", "New Price ($)", "Delta ($)", "Change (%)", "Event Type"
            ], "0F766E")

            try:
                wb.save(self.excel_path)
            except Exception:
                pass

    def _apply_headers(self, ws, headers: List[str], header_color: str):
        ws.append(headers)
        fill = PatternFill(start_color=header_color, end_color=header_color, fill_type="solid")
        font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = fill
            cell.font = font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 28

    def update_with_diff_report(self, snapshot: CompetitorSnapshot, diff_report: DiffReport):
        try:
            wb = openpyxl.load_workbook(self.excel_path)
        except Exception:
            wb = openpyxl.Workbook()
            wb.create_sheet(title="Price Change History")

        # 1. Update Overview Sheet
        if "Current Pricing Overview" not in wb.sheetnames:
            ws_overview = wb.create_sheet(title="Current Pricing Overview", index=0)
        else:
            ws_overview = wb["Current Pricing Overview"]

        existing_rows = list(ws_overview.iter_rows(values_only=True))
        headers = existing_rows[0] if existing_rows else []
        retained_rows = [row for row in existing_rows[1:] if row and row[0] != snapshot.competitor_name]
        
        ws_overview.delete_rows(1, ws_overview.max_row + 1)
        self._apply_headers(ws_overview, list(headers) or [
            "Competitor Name", "Category", "Service / Product", "Current Price ($)", "Unit / Frequency", "Last Verified Date"
        ], "1E3A8A")

        for r in retained_rows:
            ws_overview.append(r)

        today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        for item in snapshot.items:
            ws_overview.append([
                snapshot.competitor_name,
                item.category,
                item.name,
                item.price,
                item.unit or "session",
                today_str
            ])

        # 2. Append to Change History Sheet
        if "Price Change History" not in wb.sheetnames:
            ws_history = wb.create_sheet(title="Price Change History")
            self._apply_headers(ws_history, [
                "Timestamp", "Competitor", "Category", "Service / Item", "Old Price ($)", "New Price ($)", "Delta ($)", "Change (%)", "Event Type"
            ], "0F766E")
        else:
            ws_history = wb["Price Change History"]

        red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid") # Price hike
        green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid") # Price drop
        blue_fill = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid") # New item
        
        changes = diff_report.price_increases + diff_report.price_decreases + diff_report.new_items + diff_report.discontinued_items
        for delta in changes:
            row_vals = [
                delta.detected_at.strftime("%Y-%m-%d %H:%M"),
                delta.competitor_name,
                delta.category,
                delta.item_name,
                delta.old_price if delta.old_price is not None else "-",
                delta.new_price if delta.new_price is not None else "-",
                delta.delta_amount if delta.delta_amount is not None else "-",
                f"{delta.delta_percentage:+.1f}%" if delta.delta_percentage is not None else "-",
                delta.change_type.replace("_", " ")
            ]
            ws_history.append(row_vals)
            cur_row = ws_history.max_row
            
            if delta.change_type == "PRICE_INCREASE":
                fill_to_apply = red_fill
            elif delta.change_type == "PRICE_DECREASE":
                fill_to_apply = green_fill
            elif delta.change_type == "NEW_ITEM":
                fill_to_apply = blue_fill
            else:
                fill_to_apply = None

            if fill_to_apply:
                for c in range(1, len(row_vals) + 1):
                    ws_history.cell(row=cur_row, column=c).fill = fill_to_apply

        for sheet in [ws_overview, ws_history]:
            for col in sheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                sheet.column_dimensions[col_letter].width = max(max_len + 4, 14)

        try:
            wb.save(self.excel_path)
        except PermissionError:
            fallback_path = self.excel_path.replace(".xlsx", f"_{datetime.now().strftime('%H%M%S')}.xlsx")
            wb.save(fallback_path)
            print(f"      [NOTE] Main Excel file was open/locked; saved update to: {fallback_path}")
            return fallback_path

        return self.excel_path
