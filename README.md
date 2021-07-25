# Suma product pricing scraper

A tool for scraping pricing information from sumawholesale.com. Useful for
communal purchase orders.

## Installation

`python -m pip install -r requirements.txt`

## Usage

1. Launch the web server: `python -m flask run`
2. Then navigate to 127.0.0.1:5000 in a browser.
3. Enter whitespace seperated list of 5 character Suma product codes to query.

## Future development

- Make requests asynchronously for faster response.
- On a code which is constructed correctly but has no product, e.g. AB123,
rather than raising ValueError, start building a list of these and return that
as a response to user.
- Containerise the app, freezing dependencies and hopefully making it less
brittle.
- Tart up the form with some CSS and nicer HTML.
