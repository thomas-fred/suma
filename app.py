import re
import logging
import sys

from flask import Flask

from client import Suma

app = Flask(__name__)

LOGGER = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# regex pattern to match a Suma code (must be entire string)
#    ^             start of string
#    [a-zA-Z]{2}   exactly 2 of latin alphabet, either case
#    [0-9]{3}      exactly 3 arabic numerals
#    $             end of string
CODE_REGEX = r"^[a-zA-Z]{2}[0-9]{3}$"

# every Suma code is 5 characters long
CODE_LEN = 5


@app.route("/<string:concat_codes>")
def convert(concat_codes):
    """
    Get pricing information for given Suma codes.

    <concat_codes> should be a concatenated series of 5-character Suma
    codes to lookup e.g. AB123 and XY456 become: AB123XY456
    """

    str_len: int = len(concat_codes)

    # no codes to parse
    if str_len == 0:
        return "Please enter the Suma product codes you want the price " \
        "information for in the address bar like so: " \
        "www.thisdomain.com/AB123XYZ456"

    # check list of codes is of plausible length
    if str_len % CODE_LEN != 0:
        return f"The sequence of Suma codes you've entered is {str_len} " \
        "characters long but it should be a multiple of 5 (each code is " \
        "exactly 5 characters long)."

    # split concatenated string
    codes: list = [
        concat_codes[CODE_LEN * n: CODE_LEN * n + CODE_LEN]
        for n in range(int(str_len / CODE_LEN))
    ]

    # check codes all match the regex, if not, store them in bad_codes
    bad_codes: list = [
        code for code in codes if not re.match(CODE_REGEX, code)
    ]

    if bad_codes:
        bad_codes_str = ", ".join(bad_codes)
        return "Some of these codes don't look in the right format to me: " \
        f"[{bad_codes_str}] aren't valid :("

    # instantiate suma client object (establishes session)
    suma_client = Suma()

    # fetch the data
    display: str = ''
    for code in codes:
        data = suma_client.get_product(code)
        product: str = "{:s}\t{:s}\t{:.2f}\t{:.2f}\n".format(
            code, data['name'], data['price'], data['currentTax'] / 100
        )
        display += product

    # TODO: render the return values in HTML template

    return display


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host="0.0.0.0", debug=True, port=80)
