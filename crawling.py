from sys import stderr
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from contextlib import closing
import json

from article import Article


def extract_values(obj, key):
    arr = []

    def extract(obj, arr, key):
        """Recursively search for values of key in JSON tree."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract(v, arr, key)
                elif k == key:
                    arr.append(v.rstrip("/"))
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    results_2 = extract(obj, arr, key)
    return results_2


def get_endpoints_list():
    '''
    The result of reverse engineering the Mobile API using the Mitmproxy is the list of endpoints
    '''
    response = requests.get(
        'https://api.20min.ch/feed/sitemap?&key=276925d8d98cd956d43cd659051232f7&json&cors=m.20min.ch&lang=de')
    response_json = json.loads(response.text)

    endpoint_list = extract_values(response_json, 'path')
    # print(endpoint_list)

    # TODO add other urls for all 35 endpoints
    urls = ["https://api.20min.ch/feed/view/63?&key=276925d8d98cd956d43cd659051232f7&json&cors=m.20min.ch&lang=de"]
    new_list = []

    for url in urls:
        response_2 = requests.get(url)
        response_2_json = json.loads(response_2.text)
        new_list.extend(extract_values(response_2_json, 'adserver_url'))

    for n in new_list:
        if n not in endpoint_list:
            endpoint_list.append(n)

    return endpoint_list


def get_content_from_url(url):
    def response_ok(r):
        content_type = r.headers['Content-Type']
        return (r.status_code == 200) and ('html' in content_type)

    with closing(requests.get(url)) as response:
        return response.text if response_ok(response) else None


def get_all_pages(endpoints):
    '''
    Concatinating the string to get the full path urls
    '''
    pages = []

    for e in endpoints:
        pages.append(urljoin("https://www.20min.ch", e))

    return pages


def get_links_from_page(url):
    '''
    Getting the list of urls of the articals that can be accessed on a specific page (one endpoint)
    '''

    exceptions = 0
    links = []

    page_content = get_content_from_url(url)

    if page_content:
        page_soup = BeautifulSoup(page_content, 'html.parser')
        articles = page_soup.find_all('div', attrs={'class': 'teaser'})

        for a in articles:
            try:
                link = a.find('div', attrs={"class": "teaser_title"}).find('h2').find('a')['href']
                if "http" not in link:
                    print(link)
                    links.append(link)
            except Exception:
                # print("Error : "+ str(a))
                exceptions += 1

    else:
        stderr.write("Failed to retrieve link : " + url + "\n")
        # some of the endpoints don't match with mobile versions (https://www.20min.ch/leben/ -> http://m.20min.ch/lifestyle)

    return links


def get_json_from_articles(urls):
    '''
    Using the html content of each url that is previously extracted in order to create a Article object and serialize
    it in JSON format. The list of JSON objects is returned
    '''

    jsons = []

    for url in urls:
        url = urljoin("https://www.20min.ch/", url)

        page_content = get_content_from_url(url)

        if page_content:
            page_soup = BeautifulSoup(page_content, 'html.parser')
            story = page_soup.find('div', attrs={'class': 'story'})
            title = story.find('div', attrs={'class': 'story_titles'}).find('h1').text

            try:
                clearfix = story.find('div', attrs={'class': 'published clearfix'}).find('h4').text
            except:
                clearfix = '/'
            try:
                dateTime = story.find('div', attrs={'class': 'published clearfix'}).find('p').text.split(';')[0]
            except Exception:
                dateTime = '/'
            try:
                dateAkt = story.find('div', attrs={'class': 'published clearfix'}).find('p').find('span').text.strip(
                    "Akt: ")
            except Exception:
                dateAkt = '/'
            try:
                h3 = story.find('div', attrs={'class': 'story_titles'}).find('h3').text
            except Exception:
                h3 = '/'

            photos_videos = []
            try:
                ph = story.find('div', attrs={'class': 'story_media'}).find('div', attrs={'class': 'ginfo'}).find_all(
                    'a')
                for p in ph:
                    photos_videos.append({'description': p.text, 'url': p['href']})
            except Exception:
                # stderr.write("Error extracting photos/videos")
                pass

            try:
                video = story.find('div', attrs={'class': 'story_media'}).find('iframe')['src']
                caption = story.find('div', attrs={'class': 'story_media'}).find('div', attrs={'class': 'caption'}).text
                photos_videos.append({'description': caption, 'url': video})
            except Exception:
                # stderr.write("Error extracting photos/videos")
                pass

            story_text = []
            autor = ''

            s_text = story.find('div', attrs={'class': 'story_text'}).find_all('p')
            for s in s_text:
                try:
                    if s.attrs.get('class')[0] == 'autor':
                        autor = s.text
                except Exception:
                    story_text.append(s.text)

            article = Article(url, title, story_text, autor, clearfix, dateTime, dateAkt, photos_videos)

            jsons.append(serialise_to_json(article))
            if url == urljoin("https://www.20min.ch/", urls[0]):
                with open("json_file.json", "w") as f:
                    json.dump(article, f, default=serialise_to_json, indent=4)
        else:
            stderr.write("Failed to retrieve link : " + url + "\n")

    return jsons


def serialise_to_json(obj):
    obj_type = type(obj).__name__
    obj_dict = {'__classname__': obj_type}
    obj_dict.update(vars(obj))
    obj_dict.__delitem__('__classname__')
    return obj_dict


def gzip_data(data):
    import gzip

    for a in json_articles:
        with open("articles.txt", 'a', encoding='utf8') as f:
            json.dump(a, f)
            f.write("\n")

    f_in = open('articles.txt', 'rb')
    f_out = gzip.open('articles.txt.gz', 'wb')
    f_out.writelines(f_in)
    f_out.close()
    f_in.close()


if __name__ == '__main__':

    new_links_count = 0
    links = []

    print("Woring on getting all endpoints..")
    endpoints = get_endpoints_list()
    # ['/schweiz', '/wahlen2019', '/schweiz/zuerich', '/schweiz/bern', '/schweiz/basel', '/schweiz/zentralschweiz', '/schweiz/ostschweiz', '/switzerlanders/stories', '/ausland', '/finance', '/dna', '/bodyundsoul', '/kochenmitfooby', '/kochenmitfooby/rezepte', '/homes', '/sport', '/championsleague', '/europaleague', '/digital', '/digital/e-sport', '/lifestyle', '/wohnen', '/people', '/venty', '/community/viral', '/community/instagram', '/leben/reisen', '/wissen', '/wissen/karriere', '/longform', '/panorama/wettbewerbe', '/motor', '/digital/games', '/herzsex', '/paid-post', '/schweiz/romandie', '/schweiz/news', '/schweiz/tessin', '/wahlen2019/news']

    print("Finished getting endpoints..")
    print("Working on getting all the pages based on endpoints..")
    pages = get_all_pages(endpoints)
    print("Done with getting the pages")

    print("Getting all the links for articles..")
    # adding all urls together in one list
    for page in pages:
        new_links = get_links_from_page(page)
        new_links_count += len(new_links)
        for l in new_links:
            if l not in links:
                links.append(l)
    print("Done")
    print("Links: {}, new links total: {}".format(len(links), new_links_count))

    print("Creating JSON records for each article..")
    json_articles = get_json_from_articles(links)
    print("Done creating the JSON records")

    print("Creating file and gzip file..")
    gzip_data(json_articles)
    print("Done!")
