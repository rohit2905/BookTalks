#Thanks to Andres Torres for this code. Source: https://www.pythoncentral.io/hashing-strings-with-python/

import uuid
import hashlib

from functools import wraps
from flask import session

import requests
import urllib.parse


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# Queries the book.review_counts function of the Goodreads API
# It takes an ISBN and returns a dict containing data on the average rating and number of ratings
# on Goodreads
def get_review_counts(isbn):
    developer_key = 'eBVKMxIKL8SGityQc5TOg'

    # Build a URL to query Goodreads API (book.review_counts function), using ISBN and the globally
    # defined developer key as parameters
    base_url = "https://www.goodreads.com/book/review_counts.json?"
    query_parameters = {"isbns": isbn, "key": developer_key}
    full_url = base_url + urllib.parse.urlencode(query_parameters)

    # Make HTTP request to the URL built above
    json_data = requests.get(full_url).json()

    # Get data we need (average_rating) from the JSON response
    average_rating = json_data['books'][0]['average_rating']
    number_ratings = json_data['books'][0]['work_ratings_count']
    if not average_rating:
        average_rating = "Not found"
    if not number_ratings:
        number_ratings = "Not found"

    # Store data in dict
    review_counts_result = {'average_rating': average_rating, 'number_ratings': number_ratings}

    return review_counts_result
