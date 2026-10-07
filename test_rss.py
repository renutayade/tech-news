import urllib.request
import xml.etree.ElementTree as ET
import json
import re

from html.parser import HTMLParser
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone

RELEVANCE_KEYWORDS = [
    "artificial intelligence",
    "ai",
    "machine learning",
    "deep learning",
    "llm",
    "large language model",
    "generative ai",
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "google deepmind",
    "nvidia",
    "transformer",
    "neural network",
    "agentic",
    "ai agent",
    "data science",
    "data engineering",
    "vector database",
    "rag",
]

with open("feeds.json", "r") as file:
    feeds = json.load(file)


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def get_text(self):
        return " ".join(self.text)


def clean_html(html):
    parser = HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text().strip()


def parse_date(date_string):
    if not date_string:
        return None

    try:
        return parsedate_to_datetime(date_string)
    except (TypeError, ValueError):
        return None


def filter_recent_articles(articles, hours=24):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    recent_articles = []

    for article in articles:
        published = article["published"]

        if published is None:
            continue

        published_utc = published.astimezone(timezone.utc)

        if published_utc >= cutoff:
            recent_articles.append(article)

    return recent_articles


def extract_hn_metadata(description):
    metadata = {
        "points": None,
        "comments": None,
        "comments_url": None
    }

    points_match = re.search(r"Points:\s*(\d+)", description)

    if points_match:
        metadata["points"] = int(points_match.group(1))

    comments_match = re.search(r"# Comments:\s*(\d+)", description)

    if comments_match:
        metadata["comments"] = int(comments_match.group(1))

    comments_url_match = re.search(
        r"Comments URL:\s*(https?://\S+)",
        description
    )

    if comments_url_match:
        metadata["comments_url"] = comments_url_match.group(1)

    return metadata

# Get only relevant articles 
def is_relevant(article):
    text = (
        (article["title"] or "") + " " +
        (article["description"] or "")
    ).lower()

    for keyword in RELEVANCE_KEYWORDS:
        if keyword.lower() in text:
            return True

    return False

# Give them score on number of keywords match
def relevance_score(article):
    text = (
        (article["title"] or "") + " " +
        (article["description"] or "")
    ).lower()

    score = 0

    for keyword in RELEVANCE_KEYWORDS:
        if keyword.lower() in text:
            score += 1

    return score


def fetch_feed(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TechNews/1.0"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def parse_feed(xml, feed):
    root = ET.fromstring(xml)

    articles = []

    for item in root.findall(".//item"):

        title = item.findtext("title")
        url = item.findtext("link")
        description = clean_html(item.findtext("description") or "")
        published = item.findtext("pubDate")

        if feed["name"] == "Hacker News":
            metadata = extract_hn_metadata(description)
            description = ""
        else:
            metadata = {}

        article = {
            "source": feed["name"],
            "category": feed["category"],
            "title": title.strip() if title else None,
            "url": url.strip() if url else None,
            "description": description,
            "published": parse_date(published),
            "metadata": metadata,
        }

        articles.append(article)

    return articles


def deduplicate(articles):
    seen = set()
    unique_articles = []

    for article in articles:
        url = article["url"]

        if url and url not in seen:
            seen.add(url)
            unique_articles.append(article)

    return unique_articles


all_articles = []

for feed in feeds:
    print("Fetching:", feed["name"])

    xml = fetch_feed(feed["url"])

    articles = parse_feed(xml, feed)

    all_articles.extend(articles)

recent_articles = filter_recent_articles(all_articles)

for article in recent_articles:
    article["relevance_score"] = relevance_score(article)

''' # Old check for relevant keywords
relevant_articles = [
    article
    for article in recent_articles
    if is_relevant(article)
]
'''

relevant_articles = [
    article
    for article in recent_articles
    if article["relevance_score"] > 0
]

relevant_articles.sort(
    key=lambda article: article["relevance_score"],
    reverse=True
)

unique_articles = deduplicate(relevant_articles)


print()
print("Total articles:", len(all_articles))
print("Recent articles:", len(recent_articles))
print("Relevant articles:", len(relevant_articles))
print("Unique articles:", len(unique_articles))


print()


for article in unique_articles:
    print("Source:", article["source"])
    print("Category:", article["category"])
    print("Title:", article["title"])
    print("Published:", article["published"])
    print("Description:", article["description"])
    print("URL:", article["url"])
    print("Metadata:", article["metadata"])
    print("Relevance:", article["relevance_score"])
    print("-" * 80)

