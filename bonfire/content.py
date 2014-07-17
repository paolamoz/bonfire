import requests
from newspaper import Article
from urlparse import urlparse, urljoin

def get_resolved_url(url, timeout=4):
    """Fallback in case newspaper can't find a canonical url."""
    return requests.head(url, timeout=timeout, allow_redirects=True).url

def extract(url, html=None):
    """Extracts metadata from a URL, and returns a dict result.
    Skips downloading step if html kwarg is provided."""
    
    article = Article(url)
    if html is not None:
        article.set_html(html)
    else:
        article.download()
    article.parse()
    f = NewspaperFetcher(article)

    canonical_url = f.get_canonical_url() or get_resolved_url(url) or url
    result = {
        'url': canonical_url.rstrip('/'),
        'title': f.get_title() or '',
        'description': f.get_description() or '',
        'text': article.text or '',
        'published': f.get_published() or None,
        'authors': f.get_authors() or '',
        'img': f.get_image(),
        'player': article.meta_data['twitter'].get('player', {}).get('url', ''),
        'favicon': f.get_favicon(),
        'raw_html': article.html or '',
        'tags': f.get_tags(),
        'opengraph_type': article.meta_data['og'].get('type', ''),
        'twitter_type': article.meta_data['twitter'].get('card', ''),
        'twitter_creator': article.meta_data['twitter'].get('creator', '').lstrip('@')
    }
    return result

class NewspaperFetcher(object):
    """
    Smartly fetches metadata from a newspaper article, and cleans the results.
    """

    def __init__(self, newspaper_article):
        self.article = newspaper_article

    def _add_domain(self, url):
        """Adds the domain if the URL is relative."""
        if url.startswith('http'):
            return url
        parsed_uri = urlparse(self.get_canonical_url())
        domain = "{uri.scheme}://{uri.netloc}".format(uri=parsed_uri)
        return urljoin(domain, url)

    def get_canonical_url(self):
        return self.article.canonical_link.strip() or \
               self.article.meta_data['og'].get('url', '').strip() or \
               self.article.meta_data['twitter'].get('url', '').strip()

    def get_title(self):
        return self.article.title.strip() or \
               self.article.meta_data['og'].get('title', '').strip() or \
               self.article.meta_data['twitter'].get('title', '').strip()

    def get_description(self):
        return self.article.summary.strip() or \
               self.article.meta_description.strip() or \
               self.article.meta_data['og'].get('description', '') or \
               self.article.meta_data['twitter'].get('description', '')

    def get_favicon(self):
        return self._add_domain(self.article.meta_favicon)

    def get_twitter_image(self):
        img = self.article.meta_data['twitter'].get('image', '')
        # Sometimes the image is at "twitter:image:src" rather than "twitter:image"
        if isinstance(img, dict):
            img = img['src']
        return img

    def get_image(self):
        result = self.article.top_image or \
                 self.article.meta_data['og'].get('image', '') or \
                 self.get_twitter_image()
        return self._add_domain(result)

    def get_published(self):
        return self.article.published_date.strip() or \
               self.article.meta_data['og'].get('article', {}).get('published_time')

    def get_authors(self):
        return ', '.join(self.article.authors) or \
               self.article.meta_data['og'].get('article', {}).get('author', '')

    def get_tags(self):
        """Retrives aggregate of all tags; opengraph tags/sections, keywords, meta_keywords, tags."""
        og_results = self.article.meta_data['og'].get('tag', '').split(',') + \
                     [self.article.meta_data['og'].get('section', '')]
        all_candidates = list(set(self.article.keywords + self.article.meta_keywords + list(self.article.tags) + og_results))
        return ', '.join(filter(lambda i: i, all_candidates))
