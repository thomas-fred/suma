import re
import logging
import sys

from flask import Flask, request, render_template
from flask_table import Table, Col

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


@app.route('/')
def input_form():
    return render_template('form.html')


@app.route('/', methods=['POST'])
def convert():
    """
    Get pricing information for given Suma codes.
    """
    text = request.form['text']

    # no codes to parse
    if len(text) == 0:
        return (
            "Please enter the Suma product codes you want the price "
            "information for in the form like so: AB123 JK456 YZ789"
        )

    # split form input by whitespace into codes
    codes = text.split()

    # check codes all match the regex, if not, store them in bad_codes
    bad_codes: list = [
        code for code in codes if not re.match(CODE_REGEX, code)
    ]

    if bad_codes:
        bad_codes_str = ", ".join(bad_codes)
        return (
            "Some of these codes don't look in the right format to me: "
            f"[{bad_codes_str}] aren't valid :("
        )

    # instantiate suma client object (establishes session)
    suma_client = Suma()

    # fetch the data and store in list of dicts
    results: list = []
    for code in codes:
        data = suma_client.get_product(code)
        data['code'] = code
        # insert quantity column to match spreadsheet schema
        data['quantity'] = ''
        results.append(data)

    # Declare your table
    class ItemTable(Table):
        code = Col('Code')
        name = Col('Name')
        price = Col('Price ex-VAT (£)')
        quantity = Col('Quantity')
        currentTax = Col('VAT rate (%)')

    # Populate the html table
    table = ItemTable(results)

    # Print the html
    return table.__html__()


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host="0.0.0.0", debug=True, port=80)
