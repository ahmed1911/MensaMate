#!/usr/bin/env python3

"""
HWR Mensa Email Bot (Refactored)
================================

Automated email bot for the HWR Berlin Mensa.
Downloads the weekly menu, filters relevant dishes, and sends them via email.

Features:
    - Automatic download of the current menu (PDF)
    - Extraction of dishes for today and tomorrow
    - Filtering of ingredients or allergens via .env configuration
    - SMTP dispatch to multiple recipients
    - Centralized configuration via .env file

Author: Ahmed Bauer (Refactored by Gemini)
Date: Oktober 2025
"""

import io
import os
import re
import smtplib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
import pdfplumber
from dotenv import load_dotenv

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()


# --- Constants ---
WEEKDAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

# Regex for parsing PDF content
PRICE_LINE_RE = re.compile(r"(\d{1,2},\d{2})\s*€\s*\|\s*(\d{1,2},\d{2})\s*€\s*\|\s*(\d{1,2},\d{2})\s*€")
ALLERGEN_TAIL_RE = re.compile(r"(.*?)\s*(\([0-9,\s\.a-z]+\))\s*$")
ALLERGEN_MAP_RE = re.compile(r"(\d+[a-z]?)\s+([A-ZÄÖÜ][^\d\n]+?)(?=\s+\d+[a-z]?|\s*$)", re.MULTILINE)

# PDF structure constants
MENU_PAGE_INDEX = 1  # The menu is on the second page (index 1)
# Column indices in the PDF table corresponding to Monday, Tuesday, etc.
DISH_COLUMN_INDICES = [4, 8, 12, 16, 20]


@dataclass
class Config:
    """Centralized configuration loaded from environment variables."""
    # PDF URL
    pdf_url: str = os.getenv("MENSA_PDF_URL", "https://www.stw.berlin/assets/speiseplaene/526/aktuelle_woche_de.pdf")

    # Email settings
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", 465))
    smtp_email: Optional[str] = os.getenv("SMTP_EMAIL")
    smtp_password: Optional[str] = os.getenv("SMTP_PASSWORD")
    recipients: List[str] = field(default_factory=lambda: [r.strip() for r in os.getenv("RECIPIENTS", "").split(",") if r.strip()])

    # Filtering
    filter_words_raw: str = os.getenv("FILTER_WORDS", "")
    filter_allergens_raw: str = os.getenv("FILTER_ALLERGENS", "")

    # Debug
    debug_mode: bool = os.getenv("DEBUG", "false").lower() == "true"

    def __post_init__(self):
        """Validate required configuration after initialization."""
        if not self.smtp_email or not self.smtp_password or not self.recipients:
            raise ValueError("Missing email config. Please set SMTP_EMAIL, SMTP_PASSWORD, and RECIPIENTS in .env")

    @property
    def filter_words(self) -> Set[str]:
        return {word.strip().lower() for word in self.filter_words_raw.split(",") if word.strip()}

    @property
    def filter_allergen_names(self) -> Set[str]:
        return {name.strip().lower() for name in self.filter_allergens_raw.split(",") if name.strip()}


@dataclass
class Dish:
    """A structured representation of a single dish."""
    title: str
    price: float
    category: str  # 'main' or 'side'
    allergens: Set[str] = field(default_factory=set)


class MensaParser:
    """Handles downloading and parsing the Mensa PDF."""

    def __init__(self, pdf_content: bytes, config: Config):
        self.pdf_content = pdf_content
        self.config = config
        self.allergen_map = self._extract_allergen_mapping()
        self.filter_allergen_numbers = self._resolve_filter_allergens()

    @staticmethod
    def download(url: str) -> bytes:
        """Downloads the Mensa PDF from the server."""
        logging.info("📥 Downloading latest menu...")
        headers = {"User-Agent": "Mozilla/5.0 (compatible; MensaBot/1.0)"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        logging.info("✅ Download complete.")
        return response.content

    def _extract_allergen_mapping(self) -> Dict[str, str]:
        """Extracts the allergen number-to-name mapping from the last PDF page."""
        allergen_map = {}
        with pdfplumber.open(io.BytesIO(self.pdf_content)) as pdf:
            last_page_text = pdf.pages[-1].extract_text()

        for match in ALLERGEN_MAP_RE.finditer(last_page_text):
            number, name = match.group(1), match.group(2).strip()
            # Clean up the extracted name
            name_clean = re.sub(r"\s*\([^)]+\)|:$", "", name).strip().lower()
            if len(name_clean) < 3:
                continue

            allergen_map[name_clean] = number
            first_word = name_clean.split()[0]
            if first_word != name_clean:
                allergen_map[first_word] = number

        if self.config.debug_mode:
            logging.debug(f"Found {len(allergen_map)} allergen mappings.")
        return allergen_map

    def _resolve_filter_allergens(self) -> Set[str]:
        """Converts allergen filter names (e.g., 'soja') to numbers (e.g., '28')."""
        resolved_allergens = set()
        for name in self.config.filter_allergen_names:
            if name in self.allergen_map:
                number = self.allergen_map[name]
                resolved_allergens.add(number)
                logging.info(f"✓ Filtering allergen '{name}' -> code '{number}'")
            else:
                logging.warning(f"⚠️ Allergen filter '{name}' not found in PDF mapping.")
        return resolved_allergens

    def _merge_table_cells(self, table: List[List[str]]) -> Dict[str, List[Dict[str, any]]]:
        """Merges dish descriptions that span multiple rows in the PDF table."""
        merged_cells = {day: [] for day in WEEKDAYS_DE[:5]}
        for row in table:
            if not row or len(row) < max(DISH_COLUMN_INDICES) + 1:
                continue

            for day, col_idx in zip(WEEKDAYS_DE[:5], DISH_COLUMN_INDICES):
                cell_text = row[col_idx]
                if not cell_text or not cell_text.strip():
                    continue

                has_price = any(PRICE_LINE_RE.search(line) for line in cell_text.splitlines())
                # If the previous cell for this day had no price, merge this one into it
                if merged_cells[day] and not merged_cells[day][-1]['has_price']:
                    merged_cells[day][-1]['text'] += '\n' + cell_text
                    merged_cells[day][-1]['has_price'] = has_price
                else:
                    merged_cells[day].append({'text': cell_text, 'has_price': has_price})
        return merged_cells

    def _parse_dish_from_cell(self, cell_text: str) -> Optional[Dish]:
        """Parses a single dish from a merged table cell."""
        lines = [line.strip() for line in cell_text.splitlines() if line.strip()]
        if not lines:
            return None

        price_match, price_idx = None, -1
        for i, line in reversed(list(enumerate(lines))):
            match = PRICE_LINE_RE.search(line)
            if match:
                price_match, price_idx = match, i
                break

        # Extract title and price
        title_lines = lines[:price_idx] if price_idx != -1 else lines
        full_title = re.sub(r'-\s+|\s+', ' ', " ".join(title_lines)).strip()
        price = float(price_match.group(1).replace(",", ".")) if price_match else None

        # Extract allergens from title
        allergen_match = ALLERGEN_TAIL_RE.match(full_title)
        if allergen_match:
            title = allergen_match.group(1).strip()
            allergens = {code.strip() for code in allergen_match.group(2).strip("()").split(",") if code.strip()}
        else:
            title, allergens = full_title, set()

        # Apply filters
        if price is None or len(title) < 5:
            return None
        if self.config.filter_words and any(word in title.lower() for word in self.config.filter_words):
            return None
        if self.filter_allergen_numbers and allergens.intersection(self.filter_allergen_numbers):
            return None

        return Dish(
            title=title,
            price=price,
            category="side" if price <= 1.0 else "main",
            allergens=allergens
        )

    def get_all_dishes(self) -> Dict[str, List[Dish]]:
        """Orchestrates the entire PDF parsing process."""
        logging.info("📄 Parsing PDF to extract dishes...")
        dishes_by_day = {day: [] for day in WEEKDAYS_DE}
        with pdfplumber.open(io.BytesIO(self.pdf_content)) as pdf:
            if len(pdf.pages) <= MENU_PAGE_INDEX:
                logging.error("PDF has fewer pages than expected. Cannot find menu.")
                return dishes_by_day

            table = pdf.pages[MENU_PAGE_INDEX].extract_table()
            if not table:
                logging.error("Could not extract table from PDF page.")
                return dishes_by_day

            merged_cells = self._merge_table_cells(table)
            for day, cells in merged_cells.items():
                for cell in cells:
                    dish = self._parse_dish_from_cell(cell['text'])
                    if dish:
                        dishes_by_day[day].append(dish)

        total_dishes = sum(len(d) for d in dishes_by_day.values())
        logging.info(f"✅ Found {total_dishes} dishes across all days.")
        return dishes_by_day


class EmailNotifier:
    """Handles the formatting and sending of the notification email."""

    def __init__(self, config: Config):
        self.config = config

    def _format_dish_section(self, dishes: List[Dish], title: str) -> str:
        """Formats a list of dishes into an HTML section."""
        if not dishes:
            return ""

        # Sort dishes by price
        sorted_dishes = sorted(dishes, key=lambda d: d.price)

        html = f'<h3>{title}</h3>'
        for dish in sorted_dishes:
            html += f'<p><b>{dish.title}</b><br>{dish.price:.2f}€</p>'
        return html

    def _format_html_body(self, dishes_by_day: Dict[str, List[Dish]]) -> str:
        """Creates the full HTML email body."""
        today_idx = datetime.now().weekday()
        html = '<html><head><style>body { font-family: sans-serif; } h2, h3 { color: #333; } p { margin: 0.5em 0; }</style></head><body>'
        html += '<h1>HWR Mensa Menü</h1><hr>'

        days_to_show = []
        if today_idx < 5:  # Monday to Friday
            days_to_show.append(("Heute", WEEKDAYS_DE[today_idx]))
        if today_idx < 4:  # Monday to Thursday (show tomorrow)
            days_to_show.append(("Morgen", WEEKDAYS_DE[today_idx + 1]))

        if not days_to_show:
            html += "<p>Schönes Wochenende! Keine Gerichte für heute oder morgen verfügbar.</p>"
        else:
            for label, day_name in days_to_show:
                day_dishes = dishes_by_day.get(day_name, [])
                html += f'<h2>{label} ({day_name})</h2>'
                if not day_dishes:
                    html += '<p>Keine Gerichte verfügbar.</p>'
                else:
                    main_dishes = [d for d in day_dishes if d.category == 'main']
                    side_dishes = [d for d in day_dishes if d.category == 'side']
                    html += self._format_dish_section(main_dishes, "🥗 Hauptgerichte")
                    html += self._format_dish_section(side_dishes, "🥔 Beilagen")
                html += '<br>'

        html += '<hr><p><small>Automatisch generiert vom HWR Mensa Bot.</small></p>'
        html += '</body></html>'
        return html

    def send(self, dishes_by_day: Dict[str, List[Dish]]):
        """Sends the formatted email to all configured recipients."""
        html_content = self._format_html_body(dishes_by_day)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Mensa HWR - {datetime.now().strftime('%d.%m')}"
        msg["From"] = self.config.smtp_email
        msg["To"] = ", ".join(self.config.recipients)
        msg.attach(MIMEText(html_content, "html"))

        logging.info(f"📧 Sending email to {len(self.config.recipients)} recipient(s)...")
        with smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port) as server:
            server.login(self.config.smtp_email, self.config.smtp_password)
            server.sendmail(self.config.smtp_email, self.config.recipients, msg.as_string())
        logging.info(f"✅ Email sent successfully to: {', '.join(self.config.recipients)}")


def main():
    """Main execution function."""
    try:
        config = Config()
        pdf_content = MensaParser.download(config.pdf_url)
        parser = MensaParser(pdf_content, config)
        dishes = parser.get_all_dishes()

        notifier = EmailNotifier(config)
        notifier.send(dishes)
    except Exception as e:
        logging.exception(f"❌ An unexpected error occurred: {e}")
        exit(1)


if __name__ == "__main__":
    main()