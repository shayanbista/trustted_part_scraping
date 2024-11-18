import os
import json
from bs4 import BeautifulSoup
from scraper.trusted_part_scraper import TrustedPartScraper


def main():
    folder_path = "./output"
    combined_data = []
    output_filename = "../combined_data.json"

    if not os.path.exists(folder_path):
        print(f"Folder '{folder_path}' does not exist.")
        return

    os.chdir(folder_path)
    html_files = [file for file in os.listdir() if file.endswith(".html")]

    for html_file in html_files:
        with open(html_file, "r", encoding="utf-8") as file:
            content = file.read()

        if not content.strip():
            print(f"Skipped empty file: {html_file}")
            continue

        try:
            soup = BeautifulSoup(content, "html.parser")
        except Exception as parse_error:
            print(f"Error parsing file {html_file}: {parse_error}")
            continue

        scraper = TrustedPartScraper(soup)
        try:
            parsed_data = scraper.parse()
        except Exception as scraper_error:
            print(
                f"Error with TrustedPartScraper for file {html_file}: {scraper_error}"
            )
            continue

        combined_data.append(
            {"file": html_file, "data": parsed_data if parsed_data else None}
        )

    try:
        with open(output_filename, "w", encoding="utf-8") as json_file:
            json.dump(combined_data, json_file, indent=4, ensure_ascii=False)
        print(f"All data saved to {output_filename}")
    except Exception as save_error:
        print(f"Error saving combined data to {output_filename}: {save_error}")


if __name__ == "__main__":
    main()
