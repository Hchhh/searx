# ----- modified by HeJiaqing -----
# ----- collect data from Bing search engine ------

import re
from lxml import html
from searx import logger, utils
from searx.engines.archlinux import supported_languages
from searx.engines.xpath import extract_text
from searx.url_utils import urlencode
from searx.utils import match_language, gen_useragent, eval_xpath

logger = logger.getChild('bing engine')

# engine dependent config
categories = ['general']
paging = True
language_support = True
supported_languages_url = 'https://www.bing.com/account/general'
language_aliases = {'zh-CN': 'zh-CHS', 'zh-TW': 'zh-CHT', 'zh-HK': 'zh-CHT'}

# search-url
base_url = 'https://www.bing.com/'
search_string = 'search?{query}&first={offset}'


def _get_offset_from_pageno(pageno):
    return (pageno - 1) * 10 + 1


# do search-request
def request(query, params):
    offset = _get_offset_from_pageno(params.get('pageno', 0))

    if params['language'] == 'all':
        lang = 'EN'
    else:
        lang = match_language(params['language'], supported_languages, language_aliases)

    query = u'language:{} {}'.format(lang.split('-')[0].upper(), query.decode('utf-8')).encode('utf-8')

    print("*******", query)

    search_path = search_string.format(
        query=urlencode({'q': query}),
        offset=offset)

    params['url'] = base_url + search_path

    return params


# get response from search-request
def response(resp):
    results = []
    result_len = 0

    dom = html.fromstring(resp.text)
    # parse results
    for result in eval_xpath(dom, '//div[@class="sa_cc"]'):
        link = eval_xpath(result, './/h3/a')[0]
        url = link.attrib.get('href')
        title = extract_text(link)
        content = extract_text(eval_xpath(result, './/p'))

        # append result
        results.append({'url': url,
                        'title': title,
                        'content': content})

    # 国内版与国际版存在两个解析页面采用的信息标签不同，若sa_cc无法采集到信息则采用b_algo获取信息
    for result in eval_xpath(dom, '//li[@class="b_algo"]'):
        link = eval_xpath(result, './/h2/a')[0]
        url = link.attrib.get('href')
        title = extract_text(link)
        content = extract_text(eval_xpath(result, './/p'))

        # append result
        results.append({'url': url,
                        'title': title,
                        'content': content})

    try:
        result_len_container = "".join(eval_xpath(dom, '//span[@class="sb_count"]/text()'))
        result_len_container = utils.to_string(result_len_container)
        if "-" in result_len_container:
            # Remove the part "from-to" for paginated request ...
            result_len_container = result_len_container[result_len_container.find("-") * 2 + 2:]

        result_len_container = re.sub('[^0-9]', '', result_len_container)
        if len(result_len_container) > 0:
            result_len = int(result_len_container)
    except Exception as e:
        logger.debug('result error :\n%s', e)
        pass

    if _get_offset_from_pageno(resp.search_params.get("pageno", 0)) > result_len:
        return []

    results.append({'number_of_results': result_len})
    return results


# 获取网站支持语言
def _fetch_supported_languages(resp):
    supported_languages = []
    dom = html.fromstring(resp.text)
    options = eval_xpath(dom, '//div[@id="limit-languages"]//input')
    for option in options:
        code = eval_xpath(option, './@id')[0].replace('_', '-')
        if code == 'nb':
            code = 'no'
        supported_languages.append(code)

    return supported_languages
