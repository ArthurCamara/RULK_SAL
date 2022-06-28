f"""Fetch and clean docs from waybackmachine"""


import justext
import lxml
from requests.adapters import HTTPAdapter
import requests
import certifi
import urllib3
import urllib
from charset_normalizer import detect
from lxml.html.clean import Cleaner

timestamp = "20200826"

def preprocessor(dom):
    "Removes unwanted parts of DOM."
    options = {
        "processing_instructions": False,
        "remove_unknown_tags": False,
        "safe_attrs_only": False,
        "page_structure": False,
        "annoying_tags": False,
        "frames": False,
        "meta": False,
        "links": False,
        "javascript": False,
        "scripts": True,
        "comments": True,
        "style": True,
        "embedded": True,
        "forms": False,
        "kill_tags": ("head",),
    }
    cleaner = Cleaner(**options)

    return cleaner.clean_html(dom)


def clean_page(html_content):
    # Return a clean page using justext.
    try:
        paragraphs = [
            x.text
            for x in justext.justext(html_content, justext.get_stoplist("English"), preprocessor=preprocessor)
            if (not x.is_boilerplate or x.cf_class == "neargood")
        ]
    except lxml.etree.ParserError:
        paragraphs = [""]
    total_text_len = sum([len(x.split()) for x in paragraphs])
    if total_text_len == 0:
        return (0, [])
    return (total_text_len, paragraphs)

def get_current(url):
    http = urllib3.PoolManager(cert_reqs="CERT_REQUIRED", ca_certs=certifi.where())
    page_content = http.request("GET", new_url)
    _, pars = clean_page(page_content.data.decode())
    return " ".join(page_content)


def get_from_wayback(url, timestamp=timestamp):
    # print(f"trying to fetch {url} at {timestamp}")
    wayback_url = f"http://archive.org/wayback/available?url={urllib.parse.quote(url)}&timestamp={timestamp}"
    answer = requests.get(wayback_url)
    if answer.status_code != 200 or len(answer.json()['archived_snapshots'])== 0 or not answer.json()["archived_snapshots"]["closest"]["available"]:
        return ""
    new_url = answer.json()["archived_snapshots"]["closest"]["url"]
    # print(new_url)
    user_agent = {'user-agent': 'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0'}
    http = urllib3.PoolManager(cert_reqs="CERT_REQUIRED", ca_certs=certifi.where(), headers=user_agent)
    page_content = http.request("GET", new_url)
    start_comment = "<!-- BEGIN WAYBACK TOOLBAR INSERT -->"
    end_comment = "<!-- END WAYBACK TOOLBAR INSERT -->"
    try:
        page_content = page_content.data.decode()
    except UnicodeDecodeError:
        # try to get the right encoding
        encoding = detect(page_content.data)['encoding']
        page_content = page_content.data.decode(encoding)
    
    try:
        page_content = page_content.split(start_comment)[1].split(end_comment)[1].strip()
    except:
        return ""
    
    _, pars = clean_page(page_content)
    return " ".join(pars)
