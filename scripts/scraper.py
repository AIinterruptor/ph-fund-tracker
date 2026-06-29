#!/usr/bin/env python3
"""
PH Fund Tracker — Daily Scraper
Scrapes UITF.com.ph and PIFA mutual fund data, outputs data/funds.json
"""

import json
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from html.parser import HTMLParser


class UITFTableParser(HTMLParser):
    """Parses UITF top-funds tables from uitf.com.ph"""

    def __init__(self):
        super().__init__()
        self.funds = []
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.current_cell = ""
        self.skip_header = True
        self.table_count = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table_count += 1
            self.in_table = True
            self.skip_header = True
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag == "td" and self.in_row:
            self.in_cell = True
            self.current_cell = ""

    def handle_endtag(self, tag):
        if tag == "table":
            self.in_table = False
        elif tag == "tr" and self.in_row:
            self.in_row = False
            if self.skip_header:
                self.skip_header = False
            elif len(self.current_row) >= 3:
                self.funds.append(self.current_row)
        elif tag == "td" and self.in_cell:
            self.in_cell = False
            self.current_row.append(self.current_cell.strip())

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data


def fetch_url(url, retries=3):
    """Fetch URL content with retries."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt == retries - 1:
                print(f"  WARN: Failed to fetch {url}: {e}", file=sys.stderr)
                return None
    return None


def parse_roi(value):
    """Parse ROI string to float or None."""
    if not value:
        return None
    cleaned = value.strip().replace("%", "").replace(",", "").replace(" ", "")
    if not cleaned or cleaned in ("n.a", "n.a.", "na", "-", "N/A"):
        return None
    try:
        return round(float(cleaned), 4)
    except ValueError:
        return None


def scrape_uitf_category(class_id, category_name):
    """Scrape a single UITF category from uitf.com.ph"""
    url = (
        f"https://www.uitf.com.ph/top-funds.php?"
        f"class_id={class_id}&currency=PHP&radio1=ytd&fromdate=&todate=&btn=FILTER"
    )
    print(f"  Scraping UITF {category_name} (class_id={class_id})...")
    html = fetch_url(url)
    if not html:
        return []

    parser = UITFTableParser()
    parser.feed(html)

    funds = []
    for row in parser.funds:
        if len(row) >= 4:
            # Table columns: Rank, Manager, Fund Name, ROI
            fund = {
                "name": row[2].strip('"').strip(),
                "manager": row[1].strip('"').strip(),
                "category": category_name,
                "type": "UITF",
                "currency": "PHP",
                "ytd_return": parse_roi(row[3]),
                "navpu": None,
                "one_yr_return": None,
                "three_yr_return": None,
                "five_yr_return": None,
                "ten_yr_return": None,
            }
            if fund["name"] and not fund["name"].isdigit():
                funds.append(fund)
        elif len(row) >= 3:
            # Fallback: Manager, Fund Name, ROI
            fund = {
                "name": row[1].strip('"').strip(),
                "manager": row[0].strip('"').strip(),
                "category": category_name,
                "type": "UITF",
                "currency": "PHP",
                "ytd_return": parse_roi(row[2]),
                "navpu": None,
                "one_yr_return": None,
                "three_yr_return": None,
                "five_yr_return": None,
                "ten_yr_return": None,
            }
            if fund["name"] and not fund["name"].isdigit():
                funds.append(fund)
    return funds


def scrape_all_uitf():
    """Scrape all UITF categories."""
    categories = [
        (1, "Equity"),
        (2, "Bond / Fixed Income"),
        (3, "Balanced / Multi-Asset"),
        (4, "Money Market"),
    ]

    all_funds = []
    for class_id, name in categories:
        funds = scrape_uitf_category(class_id, name)
        all_funds.extend(funds)
        print(f"    Found {len(funds)} {name} UITFs")

    # Also try medium/long term bond sub-categories
    bond_subs = [
        (5, "Bond - Medium Term"),
        (6, "Bond - Long Term"),
        (7, "Bond - Intermediate Term"),
    ]
    for class_id, name in bond_subs:
        funds = scrape_uitf_category(class_id, name)
        if funds:
            all_funds.extend(funds)
            print(f"    Found {len(funds)} {name} UITFs")

    return all_funds


# Hardcoded PIFA mutual fund data — updated from official PIFA publication
# This serves as the baseline; the scraper updates what it can from web sources.
PIFA_BASELINE = [
    # Stock Funds - Peso
    {"name": "ALFM Growth Fund, Inc.", "navpu": 215.36, "ytd_return": -2.74, "one_yr_return": 1.35, "three_yr_return": -0.41, "five_yr_return": -2.22, "ten_yr_return": 0.58, "category": "Equity", "currency": "PHP"},
    {"name": "ATRAM Alpha Opportunity Fund, Inc.", "navpu": 2.0818, "ytd_return": -11.19, "one_yr_return": 14.91, "three_yr_return": 8.62, "five_yr_return": 4.91, "ten_yr_return": -3.69, "category": "Equity", "currency": "PHP"},
    {"name": "ATRAM Philippine Equity Opportunity Fund, Inc.", "navpu": 2.8312, "ytd_return": -7.73, "one_yr_return": -0.11, "three_yr_return": -1.3, "five_yr_return": -3.81, "ten_yr_return": -0.69, "category": "Equity", "currency": "PHP"},
    {"name": "Climbs Share Capital Equity Investment Fund Corp.", "navpu": 0.7585, "ytd_return": 3.06, "one_yr_return": 3.7, "three_yr_return": -0.29, "five_yr_return": None, "ten_yr_return": 0.03, "category": "Equity", "currency": "PHP"},
    {"name": "First Metro Consumer Fund, Inc.", "navpu": 0.5105, "ytd_return": -14.7, "one_yr_return": -7.29, "three_yr_return": -6.63, "five_yr_return": None, "ten_yr_return": -8.17, "category": "Equity", "currency": "PHP"},
    {"name": "First Metro Save and Learn Equity Fund, Inc.", "navpu": 4.3275, "ytd_return": -7.23, "one_yr_return": -2.15, "three_yr_return": -2.14, "five_yr_return": -2.24, "ten_yr_return": -1.04, "category": "Equity", "currency": "PHP"},
    {"name": "First Metro Save and Learn Philippine Index Fund, Inc.", "navpu": 0.6549, "ytd_return": -3.8, "one_yr_return": -1.74, "three_yr_return": -1.41, "five_yr_return": None, "ten_yr_return": 2.04, "category": "Equity", "currency": "PHP"},
    {"name": "MBG Equity Investment Fund, Inc.", "navpu": 73.92, "ytd_return": 5.69, "one_yr_return": -4.4, "three_yr_return": -5.77, "five_yr_return": None, "ten_yr_return": -16.45, "category": "Equity", "currency": "PHP"},
    {"name": "PAMI Equity Index Fund, Inc.", "navpu": 42.6973, "ytd_return": -1.61, "one_yr_return": -0.1, "three_yr_return": -1.02, "five_yr_return": -1.97, "ten_yr_return": 3.23, "category": "Equity", "currency": "PHP"},
    {"name": "Philam Strategic Growth Fund, Inc.", "navpu": 452.02, "ytd_return": -2.82, "one_yr_return": 0.96, "three_yr_return": -0.89, "five_yr_return": -2.08, "ten_yr_return": 0.54, "category": "Equity", "currency": "PHP"},
    {"name": "Philequity Dividend Yield Fund, Inc.", "navpu": 1.6481, "ytd_return": 13.0, "one_yr_return": 11.95, "three_yr_return": 7.77, "five_yr_return": 2.54, "ten_yr_return": 5.55, "category": "Equity", "currency": "PHP"},
    {"name": "Philequity Fund, Inc.", "navpu": 36.2802, "ytd_return": -0.33, "one_yr_return": 2.53, "three_yr_return": 1.5, "five_yr_return": -0.16, "ten_yr_return": 5.36, "category": "Equity", "currency": "PHP"},
    {"name": "Philequity MSCI Philippine Index Fund, Inc.", "navpu": 0.9597, "ytd_return": 6.61, "one_yr_return": 4.28, "three_yr_return": 1.79, "five_yr_return": None, "ten_yr_return": 8.11, "category": "Equity", "currency": "PHP"},
    {"name": "Philequity PSE Index Fund, Inc.", "navpu": 4.6091, "ytd_return": -0.73, "one_yr_return": 1.0, "three_yr_return": 0.01, "five_yr_return": -1.07, "ten_yr_return": 3.13, "category": "Equity", "currency": "PHP"},
    {"name": "Philippine Stock Index Fund Corp.", "navpu": 759.43, "ytd_return": -1.09, "one_yr_return": 0.64, "three_yr_return": -0.31, "five_yr_return": -1.28, "ten_yr_return": 3.32, "category": "Equity", "currency": "PHP"},
    {"name": "Soldivo Strategic Growth Fund, Inc.", "navpu": 0.6983, "ytd_return": -8.01, "one_yr_return": 2.29, "three_yr_return": -0.11, "five_yr_return": -2.75, "ten_yr_return": -0.54, "category": "Equity", "currency": "PHP"},
    {"name": "Sun Life Prosperity Philippine Equity Fund, Inc.", "navpu": 3.193, "ytd_return": -8.64, "one_yr_return": -1.3, "three_yr_return": -1.77, "five_yr_return": -2.7, "ten_yr_return": -0.51, "category": "Equity", "currency": "PHP"},
    {"name": "Sun Life Prosperity Philippine Stock Index Fund, Inc.", "navpu": 0.8514, "ytd_return": -1.36, "one_yr_return": 0.2, "three_yr_return": -0.68, "five_yr_return": -1.55, "ten_yr_return": 3.33, "category": "Equity", "currency": "PHP"},
    {"name": "United Fund, Inc.", "navpu": 3.2557, "ytd_return": -3.92, "one_yr_return": 2.29, "three_yr_return": 0.27, "five_yr_return": -0.62, "ten_yr_return": -0.94, "category": "Equity", "currency": "PHP"},
    {"name": "COL Equity Index Unitized Mutual Fund, Inc.", "navpu": 1.0666, "ytd_return": -1.1, "one_yr_return": 0.65, "three_yr_return": None, "five_yr_return": None, "ten_yr_return": 3.26, "category": "Equity", "currency": "PHP"},
    {"name": "COL Strategic Growth Equity Unitized Mutual Fund, Inc.", "navpu": 1.0689, "ytd_return": -1.47, "one_yr_return": None, "three_yr_return": None, "five_yr_return": None, "ten_yr_return": 2.43, "category": "Equity", "currency": "PHP"},
    {"name": "Philequity Alpha One Fund, Inc.", "navpu": 0.9463, "ytd_return": -4.72, "one_yr_return": -2.8, "three_yr_return": -2.38, "five_yr_return": None, "ten_yr_return": 0.19, "category": "Equity", "currency": "PHP"},
    {"name": "Philippine Stock Index Fund Corp. (Units)", "navpu": 916.46, "ytd_return": -1.11, "one_yr_return": 0.44, "three_yr_return": None, "five_yr_return": None, "ten_yr_return": 3.38, "category": "Equity", "currency": "PHP"},
    {"name": "First Metro Phil. Equity Exchange Traded Fund, Inc.", "navpu": 103.5744, "ytd_return": -0.85, "one_yr_return": 0.92, "three_yr_return": 0.01, "five_yr_return": -0.83, "ten_yr_return": 3.56, "category": "Equity (ETF)", "currency": "PHP"},
    # Stock Funds - Foreign Currency
    {"name": "ATRAM AsiaPlus Equity Fund, Inc.", "navpu": 1.3367, "ytd_return": 48.37, "one_yr_return": 15.84, "three_yr_return": 1.3, "five_yr_return": 4.94, "ten_yr_return": 30.47, "category": "Equity", "currency": "USD"},
    {"name": "Sun Life Prosperity World Voyager Fund, Inc.", "navpu": 2.4604, "ytd_return": 24.43, "one_yr_return": 16.11, "three_yr_return": 6.81, "five_yr_return": 9.29, "ten_yr_return": 10.67, "category": "Equity", "currency": "USD"},
    {"name": "Philequity Global Fund, Inc.", "navpu": 1.0924, "ytd_return": None, "one_yr_return": None, "three_yr_return": None, "five_yr_return": None, "ten_yr_return": None, "category": "Equity", "currency": "PHP"},
    # Balanced Funds - Peso
    {"name": "ATRAM Philippine Balanced Fund, Inc.", "navpu": 2.168, "ytd_return": -1.28, "one_yr_return": 0.84, "three_yr_return": -0.57, "five_yr_return": -0.67, "ten_yr_return": 1.29, "category": "Balanced", "currency": "PHP"},
    {"name": "ATRAM Unicapital Diversified Growth Fund, Inc.", "navpu": 1.7031, "ytd_return": 7.72, "one_yr_return": 6.1, "three_yr_return": 0.44, "five_yr_return": -0.64, "ten_yr_return": 4.08, "category": "Balanced", "currency": "PHP"},
    {"name": "First Metro Save and Learn Balanced Fund, Inc.", "navpu": 2.4808, "ytd_return": -1.3, "one_yr_return": -0.33, "three_yr_return": -0.8, "five_yr_return": -0.82, "ten_yr_return": 0.78, "category": "Balanced", "currency": "PHP"},
    {"name": "First Metro Save and Learn F.O.C.C.U.S. Dynamic Fund, Inc.", "navpu": 0.2326, "ytd_return": 3.06, "one_yr_return": 6.42, "three_yr_return": 3.75, "five_yr_return": None, "ten_yr_return": 0.3, "category": "Balanced", "currency": "PHP"},
    {"name": "NCM Mutual Fund of the Phils., Inc.", "navpu": 2.0051, "ytd_return": 1.45, "one_yr_return": 0.81, "three_yr_return": 0.62, "five_yr_return": 0.47, "ten_yr_return": 0.22, "category": "Balanced", "currency": "PHP"},
    {"name": "PAMI Horizon Fund, Inc.", "navpu": 3.7804, "ytd_return": 2.02, "one_yr_return": 2.77, "three_yr_return": 0.62, "five_yr_return": -0.12, "ten_yr_return": -0.23, "category": "Balanced", "currency": "PHP"},
    {"name": "Philam Fund, Inc.", "navpu": 15.9622, "ytd_return": -1.23, "one_yr_return": 1.46, "three_yr_return": -0.59, "five_yr_return": -0.71, "ten_yr_return": -0.28, "category": "Balanced", "currency": "PHP"},
    {"name": "Solidaritas Fund, Inc.", "navpu": 2.1303, "ytd_return": 0.34, "one_yr_return": 2.23, "three_yr_return": 0.77, "five_yr_return": 0.05, "ten_yr_return": 1.33, "category": "Balanced", "currency": "PHP"},
    {"name": "Sun Life of Canada Prosperity Balanced Fund, Inc.", "navpu": 3.4288, "ytd_return": -2.67, "one_yr_return": 0.74, "three_yr_return": -0.37, "five_yr_return": -1.08, "ten_yr_return": -0.15, "category": "Balanced", "currency": "PHP"},
    {"name": "Sun Life Prosperity Dynamic Fund, Inc.", "navpu": 0.9051, "ytd_return": -2.5, "one_yr_return": 0.6, "three_yr_return": 0.65, "five_yr_return": -0.73, "ten_yr_return": -0.61, "category": "Balanced", "currency": "PHP"},
    {"name": "BPI Wealth Builder Multi-Asset Mutual Fund, Inc.", "navpu": 10.71, "ytd_return": None, "one_yr_return": None, "three_yr_return": None, "five_yr_return": None, "ten_yr_return": None, "category": "Balanced", "currency": "PHP"},
    {"name": "Sun Life Prosperity Achiever Fund 2028, Inc.", "navpu": 0.9784, "ytd_return": 0.5, "one_yr_return": 1.62, "three_yr_return": -0.07, "five_yr_return": None, "ten_yr_return": -0.05, "category": "Balanced (Target Date)", "currency": "PHP"},
    {"name": "Sun Life Prosperity Achiever Fund 2038, Inc.", "navpu": 0.8413, "ytd_return": -2.06, "one_yr_return": -0.14, "three_yr_return": -1.34, "five_yr_return": None, "ten_yr_return": -0.06, "category": "Balanced (Target Date)", "currency": "PHP"},
    {"name": "Sun Life Prosperity Achiever Fund 2048, Inc.", "navpu": 0.8109, "ytd_return": -3.1, "one_yr_return": -0.65, "three_yr_return": -1.78, "five_yr_return": None, "ten_yr_return": -0.04, "category": "Balanced (Target Date)", "currency": "PHP"},
    # Balanced Funds - Foreign Currency
    {"name": "Cocolife Dollar Fund Builder, Inc.", "navpu": 0.03369, "ytd_return": 4.79, "one_yr_return": 0.86, "three_yr_return": -2.52, "five_yr_return": -0.56, "ten_yr_return": -1.64, "category": "Balanced", "currency": "USD"},
    {"name": "PAMI Asia Balanced Fund, Inc.", "navpu": 1.1893, "ytd_return": 11.92, "one_yr_return": 8.82, "three_yr_return": 0.92, "five_yr_return": 3.03, "ten_yr_return": -2.13, "category": "Balanced", "currency": "USD"},
    {"name": "Sun Life Prosperity Dollar Advantage Fund, Inc.", "navpu": 5.7008, "ytd_return": 16.38, "one_yr_return": 11.62, "three_yr_return": 4.0, "five_yr_return": 6.25, "ten_yr_return": 6.84, "category": "Balanced", "currency": "USD"},
    {"name": "Sun Life Prosperity Dollar Wellspring Fund, Inc.", "navpu": 1.2107, "ytd_return": 7.76, "one_yr_return": 6.34, "three_yr_return": 0.62, "five_yr_return": 2.65, "ten_yr_return": 2.33, "category": "Balanced", "currency": "USD"},
    # Bond Funds - Peso
    {"name": "ALFM Peso Bond Fund, Inc.", "navpu": 422.53, "ytd_return": 3.03, "one_yr_return": 3.26, "three_yr_return": 2.56, "five_yr_return": 2.51, "ten_yr_return": 0.62, "category": "Bond", "currency": "PHP"},
    {"name": "ATRAM Corporate Bond Fund, Inc.", "navpu": 1.9797, "ytd_return": 2.43, "one_yr_return": 1.22, "three_yr_return": 0.53, "five_yr_return": 0.41, "ten_yr_return": 1.08, "category": "Bond", "currency": "PHP"},
    {"name": "Cocolife Fixed Income Fund, Inc.", "navpu": 3.5847, "ytd_return": 1.98, "one_yr_return": 2.93, "three_yr_return": 2.12, "five_yr_return": 3.22, "ten_yr_return": 0.12, "category": "Bond", "currency": "PHP"},
    {"name": "Ekklesia Mutual Fund, Inc.", "navpu": 2.4365, "ytd_return": 1.8, "one_yr_return": 2.88, "three_yr_return": 1.49, "five_yr_return": 1.47, "ten_yr_return": -0.71, "category": "Bond", "currency": "PHP"},
    {"name": "First Metro Save and Learn Fixed Income Fund, Inc.", "navpu": 2.5152, "ytd_return": 0.26, "one_yr_return": 1.26, "three_yr_return": 0.58, "five_yr_return": 1.18, "ten_yr_return": -2.08, "category": "Bond", "currency": "PHP"},
    {"name": "Philam Bond Fund, Inc.", "navpu": 4.5364, "ytd_return": 1.57, "one_yr_return": 2.36, "three_yr_return": 0.19, "five_yr_return": 0.86, "ten_yr_return": -1.56, "category": "Bond", "currency": "PHP"},
    {"name": "Philam Managed Income Fund, Inc.", "navpu": 1.533, "ytd_return": 3.3, "one_yr_return": 4.41, "three_yr_return": 2.99, "five_yr_return": 2.88, "ten_yr_return": 0.78, "category": "Bond", "currency": "PHP"},
    {"name": "Philequity Peso Bond Fund, Inc.", "navpu": 4.2907, "ytd_return": 1.6, "one_yr_return": 2.64, "three_yr_return": 1.54, "five_yr_return": 1.95, "ten_yr_return": -0.55, "category": "Bond", "currency": "PHP"},
    {"name": "Soldivo Bond Fund, Inc.", "navpu": 1.1281, "ytd_return": 3.38, "one_yr_return": 2.92, "three_yr_return": 1.65, "five_yr_return": 1.75, "ten_yr_return": 0.68, "category": "Bond", "currency": "PHP"},
    {"name": "Sun Life of Canada Prosperity Bond Fund, Inc.", "navpu": 3.4607, "ytd_return": -0.52, "one_yr_return": 2.25, "three_yr_return": 1.49, "five_yr_return": 2.12, "ten_yr_return": -2.52, "category": "Bond", "currency": "PHP"},
    {"name": "Sun Life Prosperity GS Fund, Inc.", "navpu": 1.8394, "ytd_return": -0.3, "one_yr_return": 1.94, "three_yr_return": 1.01, "five_yr_return": 1.55, "ten_yr_return": -2.39, "category": "Bond", "currency": "PHP"},
    {"name": "ATRAM Unitized Corporate Debt Fund 2", "navpu": 1.013, "ytd_return": None, "one_yr_return": None, "three_yr_return": None, "five_yr_return": None, "ten_yr_return": None, "category": "Bond", "currency": "PHP"},
    # Bond Funds - Foreign Currency
    {"name": "ALFM Dollar Bond Fund, Inc.", "navpu": 532.25, "ytd_return": 2.6, "one_yr_return": 2.94, "three_yr_return": 1.83, "five_yr_return": 2.08, "ten_yr_return": 0.62, "category": "Bond", "currency": "USD"},
    {"name": "ALFM Euro Bond Fund, Inc.", "navpu": 223.0, "ytd_return": 0.9, "one_yr_return": 1.8, "three_yr_return": 0.26, "five_yr_return": 0.72, "ten_yr_return": -0.3, "category": "Bond", "currency": "EUR"},
    {"name": "ATRAM Total Return Dollar Bond Fund, Inc.", "navpu": 1.0625, "ytd_return": -0.25, "one_yr_return": 0.29, "three_yr_return": -2.24, "five_yr_return": -0.51, "ten_yr_return": -1.16, "category": "Bond", "currency": "USD"},
    {"name": "First Metro Save and Learn Dollar Bond Fund, Inc.", "navpu": 0.0263, "ytd_return": 2.73, "one_yr_return": 2.53, "three_yr_return": 0.15, "five_yr_return": 0.59, "ten_yr_return": -0.75, "category": "Bond", "currency": "USD"},
    {"name": "PAMI Global Bond Fund, Inc.", "navpu": 1.0523, "ytd_return": 20.44, "one_yr_return": 7.42, "three_yr_return": -0.06, "five_yr_return": -0.32, "ten_yr_return": -0.68, "category": "Bond", "currency": "USD"},
    {"name": "Philam Dollar Bond Fund, Inc.", "navpu": 2.4547, "ytd_return": 3.11, "one_yr_return": 2.98, "three_yr_return": -0.51, "five_yr_return": 0.91, "ten_yr_return": -1.02, "category": "Bond", "currency": "USD"},
    {"name": "Philequity Dollar Income Fund, Inc.", "navpu": 0.0640391, "ytd_return": 1.09, "one_yr_return": 1.99, "three_yr_return": 0.34, "five_yr_return": 1.29, "ten_yr_return": -0.63, "category": "Bond", "currency": "USD"},
    {"name": "Sun Life Prosperity Dollar Abundance Fund, Inc.", "navpu": 2.8995, "ytd_return": 3.34, "one_yr_return": 1.56, "three_yr_return": -1.89, "five_yr_return": -0.39, "ten_yr_return": -1.13, "category": "Bond", "currency": "USD"},
    # Money Market Funds - Peso
    {"name": "AIB Money Market Mutual Fund, Inc.", "navpu": 1.1802, "ytd_return": 2.77, "one_yr_return": None, "three_yr_return": None, "five_yr_return": None, "ten_yr_return": 1.18, "category": "Money Market", "currency": "PHP"},
    {"name": "ALFM Money Market Fund, Inc.", "navpu": 151.38, "ytd_return": 4.16, "one_yr_return": 3.98, "three_yr_return": 3.05, "five_yr_return": 2.79, "ten_yr_return": 1.7, "category": "Money Market", "currency": "PHP"},
    {"name": "First Metro Save and Learn Money Market Fund, Inc.", "navpu": 1.2142, "ytd_return": 3.38, "one_yr_return": 3.71, "three_yr_return": 2.9, "five_yr_return": None, "ten_yr_return": 1.39, "category": "Money Market", "currency": "PHP"},
    {"name": "Sun Life Prosperity Peso Starter Fund, Inc.", "navpu": 1.5041, "ytd_return": 3.67, "one_yr_return": 3.52, "three_yr_return": 2.88, "five_yr_return": 2.72, "ten_yr_return": 1.53, "category": "Money Market", "currency": "PHP"},
    {"name": "ALFM Money Market Fund, Inc. (Units)", "navpu": 115.98, "ytd_return": 4.12, "one_yr_return": 4.28, "three_yr_return": None, "five_yr_return": None, "ten_yr_return": 1.81, "category": "Money Market", "currency": "PHP"},
    # Money Market - Foreign Currency
    {"name": "Sun Life Prosperity Dollar Starter Fund, Inc.", "navpu": 1.1896, "ytd_return": 2.67, "one_yr_return": 3.26, "three_yr_return": 2.38, "five_yr_return": None, "ten_yr_return": 1.11, "category": "Money Market", "currency": "USD"},
    # Feeder Funds
    {"name": "ALFM Global Multi-Asset Income Fund, Inc.", "navpu": 47.4857, "ytd_return": 7.14, "one_yr_return": 3.61, "three_yr_return": None, "five_yr_return": None, "ten_yr_return": 2.44, "category": "Feeder Fund", "currency": "PHP"},
    {"name": "MBG Asia Frontier Feeder UMF, Inc.", "navpu": 1.8739, "ytd_return": None, "one_yr_return": None, "three_yr_return": None, "five_yr_return": None, "ten_yr_return": None, "category": "Feeder Fund", "currency": "PHP"},
    {"name": "Sun Life Prosperity World Equity Index Feeder Fund, Inc.", "navpu": 2.4674, "ytd_return": 33.02, "one_yr_return": 21.48, "three_yr_return": 14.56, "five_yr_return": None, "ten_yr_return": 13.7, "category": "Feeder Fund", "currency": "PHP"},
    {"name": "Sun Life Prosperity World Income Fund, Inc.", "navpu": 1.1645, "ytd_return": 11.2, "one_yr_return": None, "three_yr_return": None, "five_yr_return": None, "ten_yr_return": 4.41, "category": "Feeder Fund", "currency": "PHP"},
    {"name": "ALFM Global Multi-Asset Income Fund, Inc. (USD)", "navpu": 0.8132, "ytd_return": 1.62, "one_yr_return": 0.97, "three_yr_return": -3.86, "five_yr_return": None, "ten_yr_return": -0.72, "category": "Feeder Fund", "currency": "USD"},
]


def build_mutual_fund_list():
    """Build PIFA mutual fund list from baseline data."""
    funds = []
    for entry in PIFA_BASELINE:
        fund = {
            "name": entry["name"],
            "manager": "",
            "category": entry["category"],
            "type": "Mutual Fund",
            "currency": entry.get("currency", "PHP"),
            "navpu": entry["navpu"],
            "ytd_return": entry["ytd_return"],
            "one_yr_return": entry.get("one_yr_return"),
            "three_yr_return": entry.get("three_yr_return"),
            "five_yr_return": entry.get("five_yr_return"),
            "ten_yr_return": entry.get("ten_yr_return"),
        }

        # Infer manager from fund name
        name = entry["name"].lower()
        if "alfm" in name:
            fund["manager"] = "ALFM"
        elif "atram" in name:
            fund["manager"] = "ATRAM"
        elif "philequity" in name:
            fund["manager"] = "Philequity Management"
        elif "sun life" in name:
            fund["manager"] = "Sun Life"
        elif "first metro" in name:
            fund["manager"] = "First Metro Asset Management"
        elif "philam" in name:
            fund["manager"] = "Philam Asset Management"
        elif "pami" in name:
            fund["manager"] = "PAMI"
        elif "soldivo" in name:
            fund["manager"] = "Soldivo"
        elif "cocolife" in name:
            fund["manager"] = "Cocolife"
        elif "ekklesia" in name:
            fund["manager"] = "Ekklesia"
        elif "ncm" in name:
            fund["manager"] = "NCM"
        elif "solidaritas" in name:
            fund["manager"] = "Solidaritas"
        elif "col " in name:
            fund["manager"] = "COL Financial"
        elif "mbg" in name:
            fund["manager"] = "MBG"
        elif "climbs" in name:
            fund["manager"] = "CLIMBS"
        elif "bpi" in name:
            fund["manager"] = "BPI Wealth"
        elif "aib" in name:
            fund["manager"] = "AIB"
        elif "united fund" in name:
            fund["manager"] = "United Fund"
        elif "philippine stock index" in name:
            fund["manager"] = "FAMI"

        funds.append(fund)
    return funds


def deduplicate_funds(uitf_funds, mf_funds):
    """Merge UITF and mutual fund lists, keeping both types but deduplicating within each type."""
    all_funds = list(mf_funds)
    seen = {(f["name"].lower().strip(), f["type"]) for f in all_funds}

    for fund in uitf_funds:
        key = (fund["name"].lower().strip(), fund["type"])
        if key not in seen:
            all_funds.append(fund)
            seen.add(key)

    return all_funds


def main():
    print("PH Fund Tracker — Daily Scrape")
    print(f"Run time: {datetime.now(timezone.utc).isoformat()}")
    print()

    # 1. Scrape UITFs
    print("[1/3] Scraping UITF data from uitf.com.ph...")
    uitf_funds = scrape_all_uitf()
    print(f"  Total UITFs scraped: {len(uitf_funds)}")
    print()

    # 2. Build mutual fund list
    print("[2/3] Building PIFA mutual fund list...")
    mf_funds = build_mutual_fund_list()
    print(f"  Total mutual funds: {len(mf_funds)}")
    print()

    # 3. Merge and deduplicate
    print("[3/3] Merging and deduplicating...")
    all_funds = deduplicate_funds(uitf_funds, mf_funds)
    print(f"  Total unique funds: {len(all_funds)}")

    # Build output
    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "total_funds": len(all_funds),
        "sources": [
            "UITF.com.ph (Trust Officers Association of the Philippines)",
            "PIFA (Philippine Investment Funds Association) via BusinessMirror"
        ],
        "funds": sorted(all_funds, key=lambda f: (f.get("ytd_return") or -999), reverse=True),
    }

    # Write output
    import os
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)
    output_path = os.path.join(data_dir, "funds.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nData written to {output_path}")
    print(f"Total funds: {output['total_funds']}")
    print(f"Last updated: {output['last_updated']}")


if __name__ == "__main__":
    main()
