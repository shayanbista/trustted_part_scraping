import time
import sys
import os
import re
import json
from scrapingbee import ScrapingBeeClient
from bs4 import BeautifulSoup
from utils.button_utils import extract_button_info


class TrustedPartScraper:
    def __init__(self, soup):
        self.soup = soup

    def parse(self):
        """Parses the entire page and writes the scraped data to a JSON file."""
        scraped_data = {}

        #  Scrape title details
        title, model, stock_availability = self.scrape_title()
        scraped_data["mfg"] = title
        scraped_data["mpn"] = model
        scraped_data["part_status"] = stock_availability

        # Scrape categories and description
        categories, description = self.scrape_categories()
        scraped_data["categories"] = categories
        scraped_data["description"] = description

        # Scrape stock and price
        stock_and_price_data = self.scrape_stock_and_price()
        if stock_and_price_data:
            scraped_data["stock_and_price"] = stock_and_price_data

        # Scrape product information
        product_informations = self.scrape_product_informations()
        scraped_data["product_information"] = product_informations

        #  Scrape similar parts
        similar_parts = self.scrape_similar_parts_serial_number()
        scraped_data["similar_parts"] = similar_parts

        # Scrape long descriptions
        long_desc = self.scrape_descriptions()
        scraped_data["long_desc"] = long_desc

        # Scrape referenced names
        referenced_names = self.scrape_referenced_names()
        scraped_data["referenced_names"] = referenced_names

        return scraped_data

    def scrape_title(self):
        """Extracts the title, model, and stock availability of the product."""
        title_tag = self.soup.find("h1")
        stock_availability = self.soup.find(
            "div",
            class_="rounded-sm font-bold text-lg px-3 py-1.5 text-success-900 bg-success-200 whitespace-nowrap",
        )
        stock_availability = (
            stock_availability.text.strip() if stock_availability else None
        )
        if title_tag:
            span_tag = title_tag.find("span")
            if span_tag:
                product_model = span_tag.text.strip()
                title_text = title_tag.text.replace(product_model, "").strip()
                return title_text, product_model, stock_availability
            else:
                title_text = title_tag.text.strip()
                return title_text, None, stock_availability
        return None, None, stock_availability

    def scrape_categories(self):
        """Extracts product categories and description."""
        category_div = self.soup.find("div", class_="flex flex-col gap-2")
        if not category_div:
            return None, None

        description_div = self.soup.find("div", class_="lg:group-[.is-sticky]:hidden")
        description = description_div.text.strip() if description_div else None

        categories = []
        category_anchors = category_div.find_all("a")
        for anchor in category_anchors:
            category_name = anchor.text.strip()
            categories.append({"category_name": category_name})

        return categories, description

    def scrape_stock_and_price(self):
        """Extracts stock and price details from the table."""
        stock_table = self.soup.find("table", {"id": "ExactMatchesTable"})
        if not stock_table:
            return None

        stock_table_body = stock_table.find("tbody")
        table_rows = stock_table_body.find_all("tr")
        thead = stock_table.find("thead")

        headers = (
            [header.get_text(strip=True) for header in thead.find_all("th")]
            if thead
            else []
        )
        if headers:
            headers.pop(-1)

        results = []
        for row in table_rows:
            data_dist = row.get("data-dist")
            data_cur = row.get("data-cur")
            data_stock = row.get("data-stock-qty")
            data_mfr = row.get("data-mfr")

            _data = {
                "data_dist": data_dist,
                "data_cur": data_cur,
                "data_stock": data_stock,
                "data_mfr": data_mfr,
                "quantity_price": [],
            }

            price_section = row.find("td", class_="text-nowrap")
            if price_section:
                sections = price_section.find_all("section", class_="flex py-0.5")
                for section in sections:
                    spans = section.find_all("span")
                    if len(spans) >= 2:
                        quantity = spans[0].get_text(strip=True)
                        price = spans[-1].get_text(strip=True)
                        _data["quantity_price"].append((quantity, price))

            for index, cell in enumerate(row.find_all("td")):
                buttons = cell.find_all("button")
                for button in buttons:
                    button.extract()

                link = cell.find("a", class_="flex justify-center items-start")
                if link:
                    _data["product_url"] = link.get("href") or None
                    _data["img_src"] = (
                        link.find("img")["src"] if link.find("img") else None
                    )
                    _data["product_name"] = link.get("title") or None

            selected_data = {
                "data_dist": _data.get("data_dist"),
                "data_cur": _data.get("data_cur"),
                "data_stock": _data.get("data_stock"),
                "data_mfr": _data.get("data_mfr"),
                "sku": _data.get("Distributor Part #"),
                "prices": _data.get("quantity_price"),
            }
            results.append(selected_data)

        return results

    def scrape_product_informations(self):
        """Extracts additional product specifications."""
        specs_container = self.soup.find("div", id="product-specs")
        if not specs_container:
            return None

        specs_data = {}
        for term, description in zip(
            specs_container.find_all("dt"), specs_container.find_all("dd")
        ):
            spec_name = term.get_text(strip=True)
            spec_value = description.get_text(strip=True)
            specs_data[spec_name] = spec_value

        return specs_data

    def scrape_similar_parts_serial_number(self):
        """Extracts serial numbers of similar parts."""

        def get_text_or_none(element):
            return element.get_text(strip=True) if element else None

        similar_parts_table = self.soup.find("table", id="SimilarPartsTable")

        if not similar_parts_table:
            return None

        similar_parts_number = []

        rows = similar_parts_table.find("tbody").find_all("tr")

        similar_name_1 = get_text_or_none(
            rows[1].select_one("td:nth-child(2) a:nth-of-type(2)")
        )
        similar_name_2 = get_text_or_none(
            rows[1].select_one("td:nth-child(3) a:nth-of-type(2)")
        )
        similar_name_3 = get_text_or_none(
            rows[1].select_one("td:nth-child(4) a:nth-of-type(2)")
        )
        similar_name_4 = get_text_or_none(
            rows[1].select_one("td:nth-child(5) a:nth-of-type(2)")
        )

        similar_parts_number.extend(
            [similar_name_1, similar_name_2, similar_name_3, similar_name_4]
        )

        return similar_parts_number

    def scrape_descriptions(self):
        """Extracts long descriptions."""

        description_ul = self.soup.select(".panel-body")

        if not description_ul:
            return None

        li_elements = description_ul[0].find_all("li")

        long_desc = " ".join([li.get_text(strip=True) for li in li_elements])

        return long_desc

    def scrape_referenced_names(self):
        """Extracts referenced names."""

        reference_names = []

        sections = self.soup.find_all("section")

        last_section = sections[-1]

        names = last_section.find_all("div")

        if not names:
            return None

        for name in names[1:]:
            raw_text = name.get_text()
            cleaned_text = " ".join(raw_text.split())
            reference_names.append(cleaned_text)
        return reference_names
