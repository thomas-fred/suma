import logging
import re
import ssl
from urllib.parse import urljoin, urlparse
from typing import Optional, Callable, Sequence
from dataclasses import dataclass

import requests
from requests import adapters
from urllib3 import poolmanager
from bs4 import BeautifulSoup


LOGGER = logging.getLogger(__name__)


class TLSAdapter(adapters.HTTPAdapter):
    """
    Suma uses an out-dated set of ciphers for agreeing a connection. Downgrade
    the security level to permit usage of older, less secure ciphers when using
    this adapter.
    """

    def init_poolmanager(self, connections, maxsize, block=False):
        """Create and initialize the urllib3 PoolManager."""
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        self.poolmanager = poolmanager.PoolManager(
                num_pools=connections,
                maxsize=maxsize,
                block=block,
                ssl_version=ssl.PROTOCOL_TLS,
                ssl_context=ctx)


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
        self.session.mount(self.base_url, TLSAdapter())

    def get_product(self, code: str) -> dict:
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

        # was running into problems with a lack of root certificates
        # N.B. certificates are a chain of trust, at the base are parent certs
        # these typically come from a trusted authority like DigiCert
        # OS may be missing these certs, can install some with certifi
        # and then point requests/urllib to them if need be
        # import certifi
        # session.request(..., verify=certifi.where())
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
                    "failed to find attr {} w/ {} on page {}".format(
                        attr.name, attr.pattern, path
                    )
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

        except AttributeError:
            # maybe tried to run find on None type returned by previous .find
            raise ValueError(f"failed to get data for {code} -- is it valid?")

        # extract the link from the product item, or none if not available
        url = product.find('a').get('href')

        # get name of product too, cutting leading and trailing whitespace
        name = product.find('a').get('title').strip()

        # return relative path
        return urlparse(url).path, name


# to extract data from selected text (currently JS), register a regex here
PRODUCT_ATTRS = [
    ProductAttribute(*data) for data in (
        # ex vat price
        ('price', r'\"productPrice\":(\d+\.?\d+)', float),
        # tax rate as a percentage
        ('currentTax', r'\"currentTax\":(\d+\.?\d*)', float),
        # is tax payable? redundant courtesy of currentTax
        # ('includeTax', r'\"includeTax\":\"(\w+)\",', bool),
    )
]
