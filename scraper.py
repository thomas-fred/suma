"""
This script takes a CSV of Suma 5-character codes and scrapes sumawholesale.com
for their pricing information, writing the results out as CSV.

The header of the input CSV should begin with the following columns. Any
subsequent columns will be ignored.

Code,Item,Item Price (ex VAT),Quant.,VAT rate

Products are identified solely by their code. The scraper will stop when it
encounters the first blank entry in the Code column.

The output file will be a copy of the input, with all columns except Code
overwritten with data retrieved from sumawholesale.com.
"""

import argparse
import logging
import sys
import re

import pandas as pd

from client import Suma


LOGGER = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


REQUIRED_HEADERS = [
    'Code', 'Item', 'Item Price (ex VAT)', 'Quant.', 'VAT rate'
]


def main(input_file_path, output_file_path):

    # load input file
    LOGGER.info(f"read input from {input_file_path}")
    df = pd.read_csv(input_file_path)

    # check start of input headers match expected values
    if REQUIRED_HEADERS != list(df.columns.values)[:len(REQUIRED_HEADERS)]:
        raise ValueError(
            f"{input_file_path} headers not as expected"
        )

    # get suma scraping client
    S = Suma()

    LOGGER.info("get product data")
    for index, row in df.iterrows():

        # e.g. AB123
        code_pattern = r"[a-zA-Z]{2}\d{3}"

        try:
            if not re.search(code_pattern, row.Code):
                # failed match returns None, which is falsy
                # can't find a correctly formatted code
                # assume we're at the end of the data and exit loop
                continue
        except TypeError:
            # can't perform regex on cell contents
            # probably nan value, so again, exit loop
            continue

        # fetch the data
        data = S.get_product(row.Code)

        # modify dataframe in-place
        df.loc[index, 'Item'] = data['name']
        df.loc[index, 'Item Price (ex VAT)'] = data['price']
        # N.B. scraper returns percentage, by convention CSV uses decimal
        df.loc[index, 'VAT rate'] = data['currentTax'] / 100

        LOGGER.info((data['name']))

    # write out to file
    LOGGER.info(f"write output to {output_file_path}")
    # do not include row index
    df.to_csv(output_file_path, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Scrape Suma product information.'
    )
    parser.add_argument('input_file', type=str)
    parser.add_argument('output_file', type=str)
    args = parser.parse_args()
    main(args.input_file, args.output_file)
