# ----- modified by HeJiaqing -----
# ----- collect data from Soso search engine ------
from urllib.parse import urlencode

from lxml import html, etree
from dateutil import parser
from datetime import datetime, timedelta
import re
from searx.engines.xpath import extract_text
from searx.languages import language_codes
from searx.utils import eval_xpath

# 引擎所属类别
categories = ['general']

# 默认设置页面以及语言
paging = True
language_support = True

# 搜索url
# base_url = 'https://startpage.com/'
# search_url = base_url + 'do/search'

base_url = "https://weixin.sogou.com/"
search_string = "weixin?type=2&{query}&ie=utf8&s_from=input&_sug_=y&_sug_type_=&w=01019900&sut=3253&sst0=1576584810616&lkt=1%2C1576584810514%2C1576584810514"

# 广告信息的xpath标签 //*[@id="3005"]/div[2]/div/div[2]/div[2]/font[2]/a/span[@class="data-tuiguang"]
# 非广告: div[@class="result"]
# results_xpath = '//div[@class="w-gl__result"]'
# link_xpath = './/a[@class="w-gl__result-title"]'
# content_xpath = './/p[@class="w-gl__description"]'
results_xpath = '//ul[@class="news-list"]//li'
link_xpath = './/div[@class="txt-box"]//h3//a'
content_xpath = './/p[@class="txt-info"]'
pubdate_xpath = './/span[@class="s2"]'


def _get_offset_from_pageno(pageno):
    return (pageno - 1) + 1


# 发送搜索请求
def request(query, params):
    # for i in range(10):
    offset = _get_offset_from_pageno(params.get('pageno', 0))

    search_path = search_string.format(
        query=urlencode({'query': query.decode('utf-8').encode('utf-8')}),
        page=0)

    search_url = base_url + search_path
    print(search_url)
    params['url'] = search_url

    # # 指定搜索语言
    # if params['language'] != 'all':
    #     language = 'english'
    #     for lc, _, _, lang in language_codes:
    #         if lc == params['language']:
    #             language = lang
    #     params['data']['language'] = language
    #     params['data']['lui'] = language

    print(params)
    return params


# 获取请求返回数据
def response(resp):
    results = []

    dom = html.fromstring(resp.text)

    # parse results from response
    for result in eval_xpath(dom, results_xpath):
        links = eval_xpath(result, link_xpath)
        if not links:
            continue
        link = links[0]
        url = link.attrib.get('href')
        print("url:", url)
        # 正则表达式去除广告
        if re.match(r"^http(s|)://(www\.)?tuiguang\.[a-z]+/aclk.*$", url):
            continue

        if re.match(r"^http(s|)://(www\.)?advertisement\.com/do/search\?.*$", url):
            continue

        # get title element
        title = extract_text(link)
        print("titel:", title)

        if eval_xpath(result, content_xpath):
            content = extract_text(eval_xpath(result, content_xpath))
        else:
            content = ''
        # content = content.split(';')[2]
        print("content:", content)

        published_date = None
        published_contents = eval_xpath(result, pubdate_xpath)
        published_content = extract_text(published_contents[0])
        # print("pubdate:",published_content)
        # 正则表达式匹配时间参数
        if re.match(r"^[1-9]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[1-2][0-9]|3[0-1])$", published_content):
            # date_pos = re.search(r"^[1-9]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[1-2][0-9]|3[0-1])$", published_content).span()
            # date_string = published_content[date_pos]
            published_date = published_content
            print(published_date)



        # 正则表达式匹配信息日期格式：XXX小时前
        elif re.match(r"[0-9]+ 小时? 前$", published_content):
            # published_date = published_content
            # date_string = published_content[date_pos]
            # published_date = parser.parse(date_string, dayfirst=True)
            published_date = published_content
            print(published_date)

            # 获取发布时间
            # published_date = datetime.now() - timedelta(days=int(re.match(r'\d+', date_string).group()))

            # content = content[date_pos:]

        if published_date:
            # append result
            results.append({'url': url,
                            'title': title,
                            'content': content,
                            'publishedDate': published_date})
        else:
            # append result
            results.append({'url': url,
                            'title': title,
                            'content': content})

    # return results
    return results
