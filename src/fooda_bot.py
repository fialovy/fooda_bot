#!/usr/bin/env python3
import datetime
import os
import random
import sys
import warnings
from lxml import html

import jinja2
import yaml
import requests
from bs4 import BeautifulSoup


HERE = os.path.realpath(os.path.dirname(__file__))
# First of all, let's be clear that this is dirty and horrible.
warnings.filterwarnings("ignore", category=UserWarning, module="bs4")

with open(HERE + "/flavor_text.yml", "r") as fp:
    FLAVOR_TEXT = yaml.load(fp)
EMOJI_KEYWORDS = FLAVOR_TEXT["emoji_keywords"]
GREETINGS = FLAVOR_TEXT["greetings"]


class FoodaEvent:
    """simple data object for extracting fooda event data from a page"""

    def __init__(self, event_html):
        self.location = event_html.find(
            "div", {"class": "myfooda-event__meta-right myfooda-vendor-location-name"}
        ).text.strip()
        self.vendor = event_html.find("div", {"class": "myfooda-event__meta-left"})
        self.vendor_name = self.vendor.find(
            "div", {"class": "myfooda-event__name"}
        ).text.strip()
        self.vendor_cuisines = self.vendor.find(
            "div", {"class": "myfooda-event__cuisines"}
        ).text.strip()
        # Possibly even add an emoji! :D
        self.cuisine_emoji = next(
            (
                emoji
                for kw, emoji in EMOJI_KEYWORDS.items()
                if kw in self.vendor_cuisines.lower()
            ),
            None,
        )


def query_fooda_events(base_url, email, password):
    """Queries Fooda website for events"""
    # Sounds tricky, but turns out their user-visible login page submits
    # to a create form, and THEN redirects you.
    login_url = f"{base_url}/create"
    referrer_url = f"{base_url}/login"
    session = requests.session()

    # Get authenticity token for login.
    # http://kazuar.github.io/scraping-tutorial/ is super helpful.
    get_token_result = session.get(login_url)
    tree = html.fromstring(get_token_result.text)
    auth_token = list(set(tree.xpath('//meta[@name="csrf-token"]/@content')))[0]

    # Prepare login data, including token friend.
    # These are the IDs of our fields...thanks, network tab!
    login_payload = {
        "user[email]": email,
        "user[password]": password,
        "authenticity_token": auth_token,
    }

    # Do teh login.
    login_result = session.post(
        login_url, data=login_payload, headers=dict(referer=referrer_url)
    )

    # We are now on the default page for 200 Cambridge Park Drive.
    homepage_soup = BeautifulSoup(login_result.text)
    fooda_events = homepage_soup.find_all("div", {"class": "myfooda-event__meta"})

    for event in fooda_events:
        event = FoodaEvent(event_html=event)
        yield event


def gather_fooda_context():
    """gathers all the context needed for a fooda template"""
    base_url = "https://app.fooda.com/"
    FOODA_EMAIL = os.environ["FOODA_EMAIL"]
    FOODA_PW = os.environ["FOODA_PW"]

    context = {
        "random_greeting": random.choice(GREETINGS),
        "current_date": datetime.date.today().strftime("%A, %d %B %Y"),
        "fooda_events": query_fooda_events(base_url, FOODA_EMAIL, FOODA_PW),
    }
    return context


def gather_food_trucks():
    """These are sorta hard-coded since there's no online source"""
    context = [
        ("Zaaki",),
        ("The Bacon Truck", "Sate"),
        ("Chicken on the Road", "SA PA",),
        ("North East of the Border", "Moyzilla",),
        ("Compliments",),
    ]
    weekday_number = datetime.datetime.today().weekday()
    try:
        trucks = context[weekday_number]
    except IndexError:
        trucks = tuple()
    return {"trucks": trucks}


def fooda_bot():
    """placeholder for more output logic"""
    jinja_env = jinja2.Environment(
        undefined=jinja2.StrictUndefined, loader=jinja2.FileSystemLoader([HERE])
    )
    jinja_template = jinja_env.get_template("fooda.j2")
    context = dict()
    context.update(gather_food_trucks())
    context.update(gather_fooda_context())
    sys.stdout.write(jinja_template.render(**context))


if __name__ == "__main__":
    fooda_bot()
