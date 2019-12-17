# ----- modified by HeJiaqing -----
# ----- collect data from Baidu search engine ------


from lxml import html
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
base_url = 'https://startpage.com/'
search_url = base_url + 'do/search'

# 广告信息的xpath标签 //*[@id="3005"]/div[2]/div/div[2]/div[2]/font[2]/a/span[@class="data-tuiguang"]
# 非广告: div[@class="result"]
results_xpath = '//div[@class="w-gl__result"]'
link_xpath = './/a[@class="w-gl__result-title"]'
content_xpath = './/p[@class="w-gl__description"]'


# 发送搜索请求
def request(query, params):
    params['url'] = search_url
    params['method'] = 'POST'
    params['data'] = {
        'query': query,
        'page': params['pageno'],
        'cat': 'web',
        'cmd': 'process_search',
        'engine0': 'v1all',
    }

    # 指定搜索语言
    if params['language'] != 'all':
        language = 'english'
        for lc, _, _, lang in language_codes:
            if lc == params['language']:
                language = lang
        params['data']['language'] = language
        params['data']['lui'] = language

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

        # 正则表达式去除google广告
        if re.match(r"^http(s|)://(www\.)?google\.[a-z]+/aclk.*$", url):
            continue

        if re.match(r"^http(s|)://(www\.)?startpage\.com/do/search\?.*$", url):
            continue

        # get title element
        title = extract_text(link)

        if eval_xpath(result, content_xpath):
            content = extract_text(eval_xpath(result, content_xpath))
        else:
            content = ''

        published_date = None

        # 正则表达式匹配时间参数
        if re.match(r"^([1-9]|[1-2][0-9]|3[0-1]) [A-Z][a-z]{2} [0-9]{4} \.\.\. ", content):
            date_pos = content.find('...') + 4
            date_string = content[0:date_pos - 5]
            published_date = parser.parse(date_string, dayfirst=True)

            content = content[date_pos:]

        # 正则表达式匹配信息日期格式：XXX天前
        elif re.match(r"^[0-9]+ days? ago \.\.\. ", content):
            date_pos = content.find('...') + 4
            date_string = content[0:date_pos - 5]

            # 获取发布时间
            published_date = datetime.now() - timedelta(days=int(re.match(r'\d+', date_string).group()))

            content = content[date_pos:]

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
