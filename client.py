import logging
import re
from urllib.parse import urljoin, urlparse
from typing import Optional, Callable, Sequence
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


LOGGER = logging.getLogger(__name__)


@dataclass
class ProductAttribute:
    """Container for product attribute information."""

    name: str
    pattern: str
    converter: Callable


class Suma:
    """
    Scraper for SumaWholesale.com
    """

    def __init__(self):
        # use TLS, otherwise redirected to home
        self.base_url = "https://www.sumawholesale.com/"
        self.session = requests.Session()

    def get_product(self, code: str):
        """Externally facing method for getting product data."""

        path, name = self._get_product_path_and_name(code)

        data = self._get_product_pricing(path)
        data['name'] = name

        return data

    def _request(self, method: str, path: str, data: dict = None):
        """
        Main contact point for requests. Constructs URL, makes request and
        checks response status.

        Args:
            method (str): HTTP method name
            path (str): Path relative to host to request
            data (dict): Data for PUT, PATCH & POST
        """

        # complete URL
        url = urljoin(self.base_url, path)

        response = self.session.request(method, url, data=data)

        # raise exception if request unsuccessful
        response.raise_for_status()

        return response

    def _get_product_pricing(self, path: str) -> dict:
        """
        Given product page path, return relevant product info

        Args:
            path (str): Relative path of product page

        Returns:
            dict: attribute name and value of data
        """

        # get text to search for data
        string = self._get_text(path)

        data = {}
        # attr is instance of ProductAttribute dataclass
        for attr in PRODUCT_ATTRS:

            try:
                # look for attribute pattern in string
                regex = re.search(attr.pattern, string)
                value: str = regex.groups()[0]

                # convert to desired type and store
                data[attr.name] = attr.converter(value)

            except AttributeError:
                LOGGER.warning(
                    f"failed to find attr {attr.name} on page {path}"
                )
                raise  # die

        return data

    def _get_text(self, path: str) -> str:
        """Get text to extract product information from.

        Args:
            path (str): Product page relative path.

        Returns:
            str: Text containing product data"""

        product_page_html = self._request('GET', path).content

        # parse html for product page data
        soup = BeautifulSoup(product_page_html, features="html.parser")

        # product info visible when logged in is stored in javascript
        main_div = soup.body.find(
            'div', attrs={'class': 'col-main', 'id': 'main'}
        )
        script = main_div.find('script', attrs={'type': 'text/javascript'})

        return script.string

    def _get_product_path_and_name(self, code: str) -> Optional[Sequence]:
        """
        Given a product code, return product page URL and name

        Args:
            code (str): 5 character alphanumeric product code

        Returns:
            str, str: Relative path of product page and product name or None if
            path or name not found
        """

        # path relative to root
        path = f"catalogsearch/result/?q={code}"

        # _request will construct full URL
        search_pg_html = self._request('GET', path).content

        # parse html for link to product page
        soup = BeautifulSoup(search_pg_html, features="html.parser")

        try:
            # listings, should only contain one product having searched by code
            listings = soup.body.find(
                'div', attrs={'class': 'listing-type-grid catalog-listing'}
            )

            # get the product from the listings list (li)
            product = listings.find('li', attrs={'class': 'item'})

            # extract the link from the product item, or none if not available
            url = product.find('a').get('href')

            # get name of product too, cutting leading and trailing whitespace
            name = product.find('a').get('title').strip()

        except AttributeError:
            # maybe tried to run find on None type returned by previous .find
            LOGGER.warning(f"failed to get path for {code}")
            raise  # die

        # return relative path
        return urlparse(url).path, name


# to extract data from selected text (currently JS), register a regex here
PRODUCT_ATTRS = (
    ProductAttribute(*data) for data in (
        # ex vat price
        ('price', r'\"productPrice\":(\d+\.?\d+)', float),
        # tax rate as a percentage
        ('currentTax', r'\"currentTax\":(\d+\.?\d*)', float),
        # is tax payable? redundant courtesy of currentTax
        # ('includeTax', r'\"includeTax\":\"(\w+)\",', bool),
    )
)
