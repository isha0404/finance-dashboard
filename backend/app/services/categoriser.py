"""Rule-based transaction categoriser.

Matches keywords in the description (case-insensitive). Positive amounts are always
"Income". It's deliberately simple and transparent: easy to test, easy to extend,
and a good baseline before reaching for machine learning.
"""
import re
from decimal import Decimal

CATEGORIES: list[str] = [
    "Income",
    "Groceries",
    "Eating Out",
    "Transport",
    "Rent & Bills",
    "Shopping",
    "Subscriptions",
    "Health",
    "Entertainment",
    "Transfers",
    "Other",
]

# Order matters: the first matching rule wins.
RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Subscriptions", ("netflix", "spotify", "disney", "prime video", "apple.com", "icloud", "youtube premium", "gym", "puregym", "the gym group")),
    ("Groceries", ("tesco", "sainsbury", "asda", "aldi", "lidl", "morrisons", "waitrose", "co-op", "m&s food", "ocado")),
    ("Eating Out", ("deliveroo", "uber eats", "just eat", "nando", "pret", "starbucks", "costa", "greggs", "mcdonald", "kfc", "restaurant", "cafe")),
    ("Transport", ("tfl", "uber", "bolt", "trainline", "national rail", "oyster", "shell", "bp", "esso", "parking")),
    ("Rent & Bills", ("rent", "council tax", "thames water", "octopus", "british gas", "edf", "bt", "virgin media", "vodafone", "ee", "o2", "three", "insurance")),
    ("Shopping", ("amazon", "argos", "primark", "zara", "h&m", "asos", "ikea", "boots", "john lewis", "ebay")),
    ("Health", ("pharmacy", "superdrug", "dentist", "nhs", "optician", "bupa")),
    ("Entertainment", ("cinema", "odeon", "vue", "steam", "playstation", "xbox", "ticketmaster", "eventbrite")),
    ("Transfers", ("transfer", "monzo", "revolut", "paypal", "savings")),
]


def _pattern(keyword: str) -> re.Pattern[str]:
    # Keywords must start at a word boundary, so "rent" matches "Rent payment" but not "current".
    # Very short keywords (e.g. "ee", "bp") must also end at one, so "ee" doesn't match "eel".
    end = r"(?![a-z0-9])" if len(keyword) <= 3 else ""
    return re.compile(r"(?<![a-z0-9])" + re.escape(keyword) + end)


_COMPILED = [(category, [_pattern(k) for k in keywords]) for category, keywords in RULES]


def categorise(description: str, amount: Decimal) -> str:
    """Return the best category for a transaction."""
    if amount > 0:
        return "Income"
    text = description.lower()
    for category, patterns in _COMPILED:
        if any(p.search(text) for p in patterns):
            return category
    return "Other"
