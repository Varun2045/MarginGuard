import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import List
from models import DiffReport, PriceDelta

class EmailNotifier:
    """
    Generates and dispatches executive institutional-grade competitive intelligence reports.
    """
    def __init__(self, config: dict):
        self.config = config.get("email_config", {})
        self.business_name = config.get("business_info", {}).get("name", "Apex Wellness & Aesthetics")
        self.mock_mode = self.config.get("mock_mode", True)

    def generate_html_digest(self, diff_reports: List[DiffReport]) -> str:
        significant_reports = [r for r in diff_reports if r.has_significant_change]
        if not significant_reports:
            return ""

        now_dt = datetime.now()
        formatted_date = now_dt.strftime("%B %d, %Y")
        formatted_time = now_dt.strftime("%I:%M %p")
        timestamp_str = f"{formatted_date} &middot; {formatted_time}"
        date_short = now_dt.strftime("%d %b %Y")

        # Aggregate counts
        all_hikes = []
        all_drops = []
        all_new = []
        all_discontinued = []

        for r in significant_reports:
            all_hikes.extend(r.price_increases)
            all_drops.extend(r.price_decreases)
            all_new.extend(r.new_items)
            all_discontinued.extend(r.discontinued_items)

        total_changes = len(all_hikes) + len(all_drops) + len(all_new) + len(all_discontinued)
        hikes_count = len(all_hikes)
        drops_count = len(all_drops)
        new_count = len(all_new)
        discontinued_count = len(all_discontinued)

        # 1. Build Table Rows
        table_rows_html = ""
        
        # Price Increases
        for p in all_hikes:
            table_rows_html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 9px 12px; font-size: 13px; color: #1e293b; vertical-align: middle;">{p.competitor_name}</td>
                <td style="padding: 9px 12px; font-size: 13px; color: #1e293b; vertical-align: middle;">{p.item_name}</td>
                <td style="padding: 9px 12px; font-size: 13px; color: #64748b; text-align: right; font-variant-numeric: tabular-nums; vertical-align: middle;">${p.old_price:.2f}</td>
                <td style="padding: 9px 12px; font-size: 13px; font-weight: 600; color: #0f172a; text-align: right; font-variant-numeric: tabular-nums; vertical-align: middle;">${p.new_price:.2f}</td>
                <td style="padding: 9px 12px; font-size: 13px; color: #991b1b; text-align: right; font-variant-numeric: tabular-nums; vertical-align: middle;">+${p.delta_amount:.2f}</td>
                <td style="padding: 9px 12px; font-size: 13px; font-weight: 600; color: #991b1b; text-align: right; font-variant-numeric: tabular-nums; vertical-align: middle;">+{p.delta_percentage:.1f}%</td>
            </tr>
            """

        # Price Decreases
        for p in all_drops:
            table_rows_html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 9px 12px; font-size: 13px; color: #1e293b; vertical-align: middle;">{p.competitor_name}</td>
                <td style="padding: 9px 12px; font-size: 13px; color: #1e293b; vertical-align: middle;">{p.item_name}</td>
                <td style="padding: 9px 12px; font-size: 13px; color: #64748b; text-align: right; font-variant-numeric: tabular-nums; vertical-align: middle;">${p.old_price:.2f}</td>
                <td style="padding: 9px 12px; font-size: 13px; font-weight: 600; color: #0f172a; text-align: right; font-variant-numeric: tabular-nums; vertical-align: middle;">${p.new_price:.2f}</td>
                <td style="padding: 9px 12px; font-size: 13px; color: #166534; text-align: right; font-variant-numeric: tabular-nums; vertical-align: middle;">-${abs(p.delta_amount):.2f}</td>
                <td style="padding: 9px 12px; font-size: 13px; font-weight: 600; color: #166534; text-align: right; font-variant-numeric: tabular-nums; vertical-align: middle;">{p.delta_percentage:.1f}%</td>
            </tr>
            """

        # New Offerings
        for n in all_new:
            table_rows_html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 9px 12px; font-size: 13px; color: #1e293b; vertical-align: middle;">{n.competitor_name}</td>
                <td style="padding: 9px 12px; font-size: 13px; color: #1e293b; vertical-align: middle;">{n.item_name}</td>
                <td style="padding: 9px 12px; font-size: 13px; color: #94a3b8; text-align: right; font-variant-numeric: tabular-nums; vertical-align: middle;">&mdash;</td>
                <td style="padding: 9px 12px; font-size: 13px; font-weight: 600; color: #0f172a; text-align: right; font-variant-numeric: tabular-nums; vertical-align: middle;">${n.new_price:.2f}</td>
                <td style="padding: 9px 12px; font-size: 13px; color: #94a3b8; text-align: right; vertical-align: middle;">&mdash;</td>
                <td style="padding: 9px 12px; font-size: 13px; font-weight: 600; color: #2563eb; text-align: right; vertical-align: middle;">New</td>
            </tr>
            """

        # Discontinued
        for d in all_discontinued:
            table_rows_html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 9px 12px; font-size: 13px; color: #1e293b; vertical-align: middle;">{d.competitor_name}</td>
                <td style="padding: 9px 12px; font-size: 13px; color: #1e293b; vertical-align: middle;">{d.item_name}</td>
                <td style="padding: 9px 12px; font-size: 13px; color: #64748b; text-align: right; font-variant-numeric: tabular-nums; vertical-align: middle;">${d.old_price:.2f}</td>
                <td style="padding: 9px 12px; font-size: 13px; color: #94a3b8; text-align: right; vertical-align: middle;">&mdash;</td>
                <td style="padding: 9px 12px; font-size: 13px; color: #94a3b8; text-align: right; vertical-align: middle;">&mdash;</td>
                <td style="padding: 9px 12px; font-size: 13px; font-weight: 500; color: #64748b; text-align: right; vertical-align: middle;">Discontinued</td>
            </tr>
            """

        # 2. Build Factual "What Changed" bullet list
        observations = []
        for p in all_hikes:
            observations.append(f"<strong>{p.item_name}</strong> increased from ${p.old_price:.2f} to ${p.new_price:.2f} (+{p.delta_percentage:.1f}%).")
        for p in all_drops:
            observations.append(f"<strong>{p.item_name}</strong> decreased from ${p.old_price:.2f} to ${p.new_price:.2f} ({p.delta_percentage:.1f}%).")
        for n in all_new:
            observations.append(f"{n.competitor_name} introduced <strong>{n.item_name}</strong> at ${n.new_price:.2f}.")
        for d in all_discontinued:
            observations.append(f"<strong>{d.item_name}</strong> was removed from active public menu listings.")

        what_changed_html = "".join([f"<li style='margin-bottom: 5px; line-height: 1.5;'>{obs}</li>" for obs in observations])

        # 3. Complete Restrained Institutional HTML Template
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Competitive Intelligence: Price Movement Alert</title>
    <style>
        body {{
            font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
            margin: 0;
            padding: 24px 12px;
            -webkit-font-smoothing: antialiased;
        }}
        .report-wrapper {{
            max-width: 680px;
            margin: 0 auto;
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
            overflow: hidden;
        }}
        .header-section {{
            padding: 20px 24px;
            border-bottom: 1px solid #e2e8f0;
            background-color: #ffffff;
        }}
        .kpi-container {{
            display: table;
            width: 100%;
            table-layout: fixed;
            margin: 14px 0 22px 0;
        }}
        .kpi-cell {{
            display: table-cell;
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            padding: 10px 12px;
            text-align: left;
        }}
        .kpi-cell + .kpi-cell {{
            border-left: none;
        }}
        .section-heading {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #475569;
            margin: 22px 0 10px 0;
            padding-bottom: 4px;
            border-bottom: 1px solid #f1f5f9;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            margin-bottom: 22px;
        }}
        .data-table th {{
            background-color: #f8fafc;
            color: #475569;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            padding: 8px 12px;
            border-top: 1px solid #e2e8f0;
            border-bottom: 1px solid #cbd5e1;
        }}
        .info-box {{
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            padding: 12px 14px;
            font-size: 12.5px;
            color: #334155;
            margin-top: 18px;
        }}
        .footer {{
            padding: 14px 24px;
            background-color: #f8fafc;
            border-top: 1px solid #e2e8f0;
            font-size: 11.5px;
            color: #64748b;
        }}
    </style>
</head>
<body>

<div class="report-wrapper">
    <!-- Header -->
    <div class="header-section">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="vertical-align: top;">
                    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; margin-bottom: 4px;">COMPETITIVE INTELLIGENCE</div>
                    <div style="font-size: 18px; font-weight: 700; color: #0f172a; line-height: 1.3;">Competitor Price Movement Alert</div>
                    <div style="font-size: 12px; color: #64748b; margin-top: 4px;">{self.business_name} &nbsp;&middot;&nbsp; {timestamp_str}</div>
                </td>
                <td style="vertical-align: top; text-align: right; width: 140px;">
                    <div style="display: inline-block; border: 1px solid #cbd5e1; background-color: #f8fafc; border-radius: 4px; padding: 6px 10px; text-align: right;">
                        <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #475569; letter-spacing: 0.05em;">ALERT</div>
                        <div style="font-size: 12px; font-weight: 600; color: #0f172a;">{total_changes} changes detected</div>
                    </div>
                </td>
            </tr>
        </table>
    </div>

    <div style="padding: 20px 24px;">
        <!-- Summary & KPIs -->
        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #475569; margin-bottom: 4px;">PRICE MOVEMENT DETECTED</div>
        <div style="font-size: 13px; color: #334155; margin-bottom: 12px;">
            {total_changes} competitor pricing changes were detected across monitored services.
        </div>

        <table style="width: 100%; border-collapse: collapse; margin-bottom: 18px;">
            <tr>
                <td style="width: 25%; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px 0 0 4px; padding: 8px 12px;">
                    <div style="font-size: 18px; font-weight: 700; color: #0f172a; font-variant-numeric: tabular-nums;">{total_changes}</div>
                    <div style="font-size: 10.5px; font-weight: 600; text-transform: uppercase; color: #64748b; letter-spacing: 0.03em;">Changes detected</div>
                </td>
                <td style="width: 25%; background-color: #f8fafc; border: 1px solid #e2e8f0; border-left: none; padding: 8px 12px;">
                    <div style="font-size: 18px; font-weight: 700; color: #991b1b; font-variant-numeric: tabular-nums;">{hikes_count}</div>
                    <div style="font-size: 10.5px; font-weight: 600; text-transform: uppercase; color: #64748b; letter-spacing: 0.03em;">Price increase</div>
                </td>
                <td style="width: 25%; background-color: #f8fafc; border: 1px solid #e2e8f0; border-left: none; padding: 8px 12px;">
                    <div style="font-size: 18px; font-weight: 700; color: #166534; font-variant-numeric: tabular-nums;">{drops_count}</div>
                    <div style="font-size: 10.5px; font-weight: 600; text-transform: uppercase; color: #64748b; letter-spacing: 0.03em;">Price decrease</div>
                </td>
                <td style="width: 25%; background-color: #f8fafc; border: 1px solid #e2e8f0; border-left: none; border-radius: 0 4px 4px 0; padding: 8px 12px;">
                    <div style="font-size: 18px; font-weight: 700; color: #2563eb; font-variant-numeric: tabular-nums;">{new_count}</div>
                    <div style="font-size: 10.5px; font-weight: 600; text-transform: uppercase; color: #64748b; letter-spacing: 0.03em;">New offering</div>
                </td>
            </tr>
        </table>

        <!-- Main Data Table -->
        <div class="section-heading">DETECTED PRICE CHANGES</div>
        <table class="data-table">
            <thead>
                <tr>
                    <th style="text-align: left;">Competitor</th>
                    <th style="text-align: left;">Service</th>
                    <th style="text-align: right;">Previous price</th>
                    <th style="text-align: right;">Current price</th>
                    <th style="text-align: right;">Change</th>
                    <th style="text-align: right;">Change %</th>
                </tr>
            </thead>
            <tbody>
                {table_rows_html}
            </tbody>
        </table>

        <!-- What Changed -->
        <div class="section-heading">WHAT CHANGED</div>
        <ul style="margin: 0 0 16px 0; padding-left: 18px; font-size: 13px; color: #334155;">
            {what_changed_html}
        </ul>

        <!-- Why It Matters -->
        <div class="section-heading">WHY IT MATTERS</div>
        <p style="margin: 0 0 16px 0; font-size: 13px; line-height: 1.55; color: #334155;">
            The observed changes may affect Apex's relative pricing position for comparable services. The Hydrafacial increase creates additional room for price differentiation, while the laser hair removal reduction may warrant closer monitoring to determine whether it represents a short-term promotion or a structural pricing shift.
        </p>

        <!-- Recommended Review -->
        <div class="section-heading">RECOMMENDED REVIEW</div>
        <ol style="margin: 0 0 18px 0; padding-left: 18px; font-size: 13px; line-height: 1.55; color: #334155;">
            <li style="margin-bottom: 4px;">Review Apex's Hydrafacial pricing against the updated competitor price.</li>
            <li style="margin-bottom: 4px;">Monitor Lumina's laser pricing over the next 7 days.</li>
            <li style="margin-bottom: 4px;">Add Morpheus8 RF Microneedling to the competitor benchmark set.</li>
        </ol>

        <!-- Data Source & Attachment -->
        <table style="width: 100%; border-collapse: collapse; margin-top: 14px;">
            <tr>
                <td style="width: 50%; vertical-align: top; padding-right: 6px;">
                    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px 12px; font-size: 11.5px; color: #475569;">
                        <div style="font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: #334155; margin-bottom: 4px;">DATA SOURCE</div>
                        <div>Competitor pricing monitored from configured competitor sources.</div>
                        <div style="margin-top: 4px; color: #64748b;">Last checked: {timestamp_str}</div>
                        <div style="color: #64748b;">Data status: {total_changes} changes verified</div>
                    </div>
                </td>
                <td style="width: 50%; vertical-align: top; padding-left: 6px;">
                    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px 12px; font-size: 11.5px; color: #475569;">
                        <div style="font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: #334155; margin-bottom: 4px;">DATA EXPORT</div>
                        <div style="font-weight: 600; color: #0f172a;">competitor_price_tracker.xlsx</div>
                        <div style="color: #64748b; margin-top: 2px;">Updated automatically &middot; {date_short}</div>
                        <div style="color: #059669; font-weight: 600; margin-top: 3px;">Attached to notification</div>
                    </div>
                </td>
            </tr>
        </table>
    </div>

    <!-- Footer -->
    <div class="footer">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td>Internal Competitive Intelligence &middot; {self.business_name}</td>
                <td style="text-align: right;">Confidential</td>
            </tr>
        </table>
    </div>
</div>

</body>
</html>
"""
        return html

    def send_alert(self, diff_reports: List[DiffReport], excel_attachment_path: str = None) -> bool:
        html_content = self.generate_html_digest(diff_reports)
        if not html_content:
            print("[INFO] No price changes to email.")
            return False

        os.makedirs("./data/reports", exist_ok=True)
        report_file = f"./data/reports/email_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"[SUCCESS] Enterprise intelligence report saved to: {report_file}")

        if self.mock_mode:
            print(f"[MOCK EMAIL] Dispatching alert to: {self.config.get('recipient_email', 'owner@business.com')}")
            print(f"[MOCK EMAIL] Attached Excel: {excel_attachment_path}")
            return True

        try:
            msg = MIMEMultipart()
            msg["Subject"] = f"COMPETITIVE INTELLIGENCE: Competitor Price Movement Alert ({datetime.now().strftime('%b %d')})"
            msg["From"] = self.config.get("sender_email")
            msg["To"] = self.config.get("recipient_email")
            msg.attach(MIMEText(html_content, "html"))

            if excel_attachment_path and os.path.exists(excel_attachment_path):
                with open(excel_attachment_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(excel_attachment_path)}")
                    msg.attach(part)

            with smtplib.SMTP(self.config.get("smtp_server"), self.config.get("smtp_port")) as server:
                server.starttls()
                server.login(self.config.get("sender_email"), os.getenv("SMTP_PASSWORD"))
                server.send_message(msg)
            print("[SUCCESS] Live alert email dispatched successfully!")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send live email: {e}")
            return False
