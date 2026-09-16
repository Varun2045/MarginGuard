import sys
import os
import json
import asyncio
import argparse
from datetime import datetime

# Ensure utf-8 encoding for terminal output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from models import MenuItem, CompetitorSnapshot, DiffReport, PriceDelta
from scraper import CompetitorScraper
from extractor import MenuExtractor
from diff_engine import DiffEngine
from excel_manager import ExcelManager
from email_notifier import EmailNotifier

def run_simulation():
    """
    Simulates a week-over-week competitor pricing update,
    updating the Excel tracker and sending the HTML email digest.
    """
    print("=" * 70)
    print(" [*] AI COMPETITOR PRICE & MENU MONITORING SENTINEL - RUNNING")
    print("=" * 70)
    
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    diff_engine = DiffEngine(snapshots_dir=config["storage"]["snapshots_dir"])
    excel_manager = ExcelManager(excel_path=config["storage"]["excel_path"])
    email_notifier = EmailNotifier(config=config)

    comp1_id = "lumina_spa"
    comp1_name = "Lumina Medical Spa & Wellness"
    
    # 1. Historical Baseline Snapshot (Week 1)
    week1_snapshot = CompetitorSnapshot(
        competitor_id=comp1_id,
        competitor_name=comp1_name,
        url="https://lumina-medspa.example.com/pricing",
        timestamp=datetime(2026, 9, 1),
        items=[
            MenuItem(name="Hydrafacial Deluxe", category="Facial Treatments", price=199.0, currency="USD"),
            MenuItem(name="Botox Cosmetic (per unit)", category="Injectables", price=13.5, currency="USD", unit="unit"),
            MenuItem(name="Full Body Laser Hair Removal", category="Laser & Body", price=350.0, currency="USD"),
            MenuItem(name="Microneedling with PRP", category="Skin Rejuvenation", price=450.0, currency="USD"),
            MenuItem(name="Chemical Peel Standard", category="Facial Treatments", price=120.0, currency="USD")
        ]
    )
    diff_engine.save_snapshot(week1_snapshot)
    print(f"\n[1/4] Baseline Snapshot Loaded: {comp1_name} ({len(week1_snapshot.items)} active services)")

    # 2. Simulated Scraped Current Week (Week 2 - Price shift detected!)
    print("[2/4] Headless Browser Agent navigated and extracted live menu...")
    week2_snapshot = CompetitorSnapshot(
        competitor_id=comp1_id,
        competitor_name=comp1_name,
        url="https://lumina-medspa.example.com/pricing",
        timestamp=datetime.now(),
        items=[
            MenuItem(name="Hydrafacial Deluxe", category="Facial Treatments", price=225.0, currency="USD"), # +$26 hike (+13.1%)
            MenuItem(name="Botox Cosmetic (per unit)", category="Injectables", price=13.5, currency="USD", unit="unit"), # Unchanged
            MenuItem(name="Full Body Laser Hair Removal", category="Laser & Body", price=299.0, currency="USD"), # -$51 drop (-14.6%) promo!
            MenuItem(name="Microneedling with PRP", category="Skin Rejuvenation", price=450.0, currency="USD"), # Unchanged
            MenuItem(name="Morpheus8 RF Microneedling", category="Skin Rejuvenation", price=750.0, currency="USD"), # New Service!
        ]
    )

    # 3. Compute Diff
    print("[3/4] Running Semantic Diff Engine...")
    prev = diff_engine.load_previous_snapshot(comp1_id)
    report = diff_engine.compute_diff(current=week2_snapshot, previous=prev, threshold_pct=config["business_info"].get("notification_threshold_pct", 0.0))

    print(f"      - Price Hikes: {len(report.price_increases)}")
    for p in report.price_increases:
        print(f"        [+] HIKE: {p.item_name}: ${p.old_price:.2f} -> ${p.new_price:.2f} (+{p.delta_percentage:.1f}%)")
    
    print(f"      - Price Drops: {len(report.price_decreases)}")
    for p in report.price_decreases:
        print(f"        [-] DROP: {p.item_name}: ${p.old_price:.2f} -> ${p.new_price:.2f} ({p.delta_percentage:.1f}%)")
    
    print(f"      - New Offerings: {len(report.new_items)}")
    for n in report.new_items:
        print(f"        [*] NEW : {n.item_name}: ${n.new_price:.2f}")

    if report.discontinued_items:
        print(f"      - Discontinued: {len(report.discontinued_items)}")
        for d in report.discontinued_items:
            print(f"        [x] REMOVED: {d.item_name}")

    # 4. Update Excel Sheet & Send Email
    print("\n[4/4] Updating Master Excel Spreadsheet & Dispatching Alerts...")
    excel_path = excel_manager.update_with_diff_report(week2_snapshot, report)
    print(f"      [OK] Excel Workbook updated: {excel_path}")

    email_sent = email_notifier.send_alert([report], excel_attachment_path=excel_path)
    
    diff_engine.save_snapshot(week2_snapshot)
    print("\n" + "=" * 70)
    print(" [OK] WORKFLOW COMPLETE: Owner notified & Excel tracker synchronized!")
    print("=" * 70)

async def run_live():
    """
    Runs live web scraping against configured targets in config.json.
    """
    print("=" * 70)
    print(" [*] RUNNING LIVE COMPETITOR SCAN")
    print("=" * 70)
    
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    scraper = CompetitorScraper(headless=True)
    extractor = MenuExtractor(provider=config.get("llm_config", {}).get("provider", "gemini"))
    diff_engine = DiffEngine(snapshots_dir=config["storage"]["snapshots_dir"])
    excel_manager = ExcelManager(excel_path=config["storage"]["excel_path"])
    email_notifier = EmailNotifier(config=config)

    diff_reports = []
    for comp in config.get("competitors", []):
        print(f"\n[SCAN] Fetching competitor: {comp['name']} ({comp['url']})")
        res = await scraper.fetch_page_content(comp["url"])
        if res.get("status") == "success":
            print(f"       [OK] Page loaded: '{res.get('title')}'")
            snapshot = extractor.extract_items_from_html(comp["id"], comp["name"], comp["url"], res.get("html", ""))
            print(f"       Extracted {len(snapshot.items)} items/services.")
            prev = diff_engine.load_previous_snapshot(comp["id"])
            report = diff_engine.compute_diff(current=snapshot, previous=prev, threshold_pct=config["business_info"].get("notification_threshold_pct", 0.0))
            diff_reports.append(report)
            excel_path = excel_manager.update_with_diff_report(snapshot, report)
            diff_engine.save_snapshot(snapshot)
        else:
            print(f"       [!] Scrape notice: {res.get('error')}")

    if any(r.has_significant_change for r in diff_reports):
        email_notifier.send_alert(diff_reports, excel_attachment_path=config["storage"]["excel_path"])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="AI Competitor Price & Menu Monitoring Sentinel")
    parser.add_argument("--live", action="store_true", help="Run live browser scrape against URLs in config.json")
    args = parser.parse_args()

    if args.live:
        asyncio.run(run_live())
    else:
        run_simulation()
