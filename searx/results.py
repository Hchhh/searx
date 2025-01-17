import re
import sys
from collections import defaultdict
from operator import itemgetter
from threading import RLock
from searx.engines import engines
from searx.url_utils import urlparse, unquote

if sys.version_info[0] == 3:
    basestring = str

CONTENT_LEN_IGNORED_CHARS_REGEX = re.compile(r'[,;:!?\./\\\\ ()-_]', re.M | re.U)
WHITESPACE_REGEX = re.compile('( |\t|\n)+', re.M | re.U)

def compare_urls(url_a, url_b):
    # ignore www. in comparison
    if url_a.netloc.startswith('www.'):
        host_a = url_a.netloc.replace('www.', '', 1)
    else:
        host_a = url_a.netloc
    if url_b.netloc.startswith('www.'):
        host_b = url_b.netloc.replace('www.', '', 1)
    else:
        host_b = url_b.netloc

    if host_a != host_b or url_a.query != url_b.query or url_a.fragment != url_b.fragment:
        return False

    # remove / from the end of the url if required
    path_a = url_a.path[:-1]\
        if url_a.path.endswith('/')\
        else url_a.path
    path_b = url_b.path[:-1]\
        if url_b.path.endswith('/')\
        else url_b.path

    return unquote(path_a) == unquote(path_b)
# return the meaningful length of the content for a result
def result_content_len(content):
    if isinstance(content, basestring):
        return len(CONTENT_LEN_IGNORED_CHARS_REGEX.sub('', content))
    else:
        return 0




def merge_two_infoboxes(infobox1, infobox2):
    # get engines weights
    if hasattr(engines[infobox1['engine']], 'weight'):
        weight1 = engines[infobox1['engine']].weight
    else:
        weight1 = 1
    if hasattr(engines[infobox2['engine']], 'weight'):
        weight2 = engines[infobox2['engine']].weight
    else:
        weight2 = 1
    if weight2 > weight1:
        infobox1['engine'] = infobox2['engine']

    if 'urls' in infobox2:
        urls1 = infobox1.get('urls', None)
        if urls1 is None:
            urls1 = []

        for url2 in infobox2.get('urls', []):
            unique_url = True
            for url1 in infobox1.get('urls', []):
                if compare_urls(urlparse(url1.get('url', '')), urlparse(url2.get('url', ''))):
                    unique_url = False
                    break
            if unique_url:
                urls1.append(url2)

        infobox1['urls'] = urls1

    if 'img_src' in infobox2:
        img1 = infobox1.get('img_src', None)
        img2 = infobox2.get('img_src')
        if img1 is None:
            infobox1['img_src'] = img2
        elif weight2 > weight1:
            infobox1['img_src'] = img2

    if 'attributes' in infobox2:
        attributes1 = infobox1.get('attributes', None)
         #----- modified by zjn -----
         # ==None->is None
        if attributes1 is None:
            
            attributes1 = []
            infobox1['attributes'] = attributes1

        attributeSet = set()
        for attribute in infobox1.get('attributes', []):
            if attribute.get('label', None) not in attributeSet:
                attributeSet.add(attribute.get('label', None))

        for attribute in infobox2.get('attributes', []):
            if attribute.get('label', None) not in attributeSet:
                attributes1.append(attribute)

    if 'content' in infobox2:
        content1 = infobox1.get('content', None)
        content2 = infobox2.get('content', '')
        if content1 is not None:
            if result_content_len(content2) > result_content_len(content1):
                infobox1['content'] = content2
        else:
            infobox1['content'] = content2

#----- modified by zjn -----
def result_score(result):
    weight = 1.0

    for result_engine in result['engines']:
        if hasattr(engines[result_engine], 'weight'):
            weight *= float(engines[result_engine].weight)

    occurences = len(result['positions'])
    # Sum(itreable,start)	从start开始遍历计算sum。
    #此处重复计算了多次。
    #return sum((occurences * weight) / position for position in result['positions'])
    tmp=occurences*weight
    return sum(tmp/position for position in result['positions'])


class ResultContainer(object):
    """docstring for ResultContainer"""

    def __init__(self):
        super(ResultContainer, self).__init__()
        self.results = defaultdict(list)
        self._merged_results = []
        self.infoboxes = []
        self.suggestions = set()
        self.answers = set()
        self.corrections = set()
        self._number_of_results = []
        self._ordered = False
        self.paging = False
        self.unresponsive_engines = set()
        self.timings = []

    def extend(self, engine_name, results):
        for result in list(results):
            result['engine'] = engine_name
            if 'suggestion' in result:
                self.suggestions.add(result['suggestion'])
                results.remove(result)
            elif 'answer' in result:
                self.answers.add(result['answer'])
                results.remove(result)
            elif 'correction' in result:
                self.corrections.add(result['correction'])
                results.remove(result)
            elif 'infobox' in result:
                self._merge_infobox(result)
                results.remove(result)
            elif 'number_of_results' in result:
                self._number_of_results.append(result['number_of_results'])
                results.remove(result)
#----- modified by zjn -----
        if engine_name in engines:
            #with Lock();
            #不加锁在多线程中可能会导致问题，增强程序健壮性
            #RLock和Lock的区别：在同一线程内，对RLock进行多次操作，程序不会阻塞。
            with RLock():
                engines[engine_name].stats['search_count'] += 1
                engines[engine_name].stats['result_count'] += len(results)

        if not results:
            return

        self.results[engine_name].extend(results)

        if not self.paging and engine_name in engines and engines[engine_name].paging:
            self.paging = True

        for i, result in enumerate(results):
            if 'url' in result and not isinstance(result['url'], basestring):
                continue
            try:
                result['url'] = result['url'].decode('utf-8')
            except:
                pass
            if 'title' in result and not isinstance(result['title'], basestring):
                continue
            if 'content' in result and not isinstance(result['content'], basestring):
                continue
            position = i + 1
            self._merge_result(result, position)

    def _merge_infobox(self, infobox):
        add_infobox = True
        infobox_id = infobox.get('id', None)
        if infobox_id is not None:
           #----- modified by zjn -----
           #此处将内层if循环提前至for循环之前
           #提前判断compare_urls(urlparse(existingIndex.get('id', '')), urlparse(infobox_id))
            for existingIndex in self.infoboxes:
                if compare_urls(urlparse(existingIndex.get('id', '')), urlparse(infobox_id)):
                    merge_two_infoboxes(existingIndex, infobox)
                    add_infobox = False

        if add_infobox:
            self.infoboxes.append(infobox)

    def _merge_result(self, result, position):
        if 'url' in result:
            self.__merge_url_result(result, position)
            return

        self.__merge_result_no_url(result, position)

    def __merge_url_result(self, result, position):
        result['parsed_url'] = urlparse(result['url'])

        # if the result has no scheme, use http as default
        if not result['parsed_url'].scheme:
            result['parsed_url'] = result['parsed_url']._replace(scheme="http")
            result['url'] = result['parsed_url'].geturl()

        result['engines'] = set([result['engine']])

        # strip multiple spaces and cariage returns from content
        if result.get('content'):
            result['content'] = WHITESPACE_REGEX.sub(' ', result['content'])

        duplicated = self.__find_duplicated_http_result(result)
        if duplicated:
            self.__merge_duplicated_http_result(duplicated, result, position)
            return

        # if there is no duplicate found, append result
        result['positions'] = [position]
        #----- modified by zjn -----
        #with Lock();
        #不加锁在多线程中可能会导致问题，增强程序健壮性
        #RLock和Lock的区别：在同一线程内，对RLock进行多次操作，程序不会阻塞。
        with RLock():
            self._merged_results.append(result)

    def __find_duplicated_http_result(self, result):
        result_template = result.get('template')
        for merged_result in self._merged_results:
            if 'parsed_url' not in merged_result:
                continue
            if compare_urls(result['parsed_url'], merged_result['parsed_url'])\
               and result_template == merged_result.get('template'):
                if result_template != 'images.html':
                    # not an image, same template, same url : it's a duplicate
                    return merged_result
                else:
                    # it's an image
                    # it's a duplicate if the parsed_url, template and img_src are differents
                    if result.get('img_src', '') == merged_result.get('img_src', ''):
                        return merged_result
        return None

    def __merge_duplicated_http_result(self, duplicated, result, position):
        # using content with more text
        if result_content_len(result.get('content', '')) >\
                result_content_len(duplicated.get('content', '')):
            duplicated['content'] = result['content']

        # merge all result's parameters not found in duplicate
        for key in result.keys():
            if not duplicated.get(key):
                duplicated[key] = result.get(key)

        # add the new position
        duplicated['positions'].append(position)

        # add engine to list of result-engines
        duplicated['engines'].add(result['engine'])

        # using https if possible
        if duplicated['parsed_url'].scheme != 'https' and result['parsed_url'].scheme == 'https':
            duplicated['url'] = result['parsed_url'].geturl()
            duplicated['parsed_url'] = result['parsed_url']

    def __merge_result_no_url(self, result, position):
        result['engines'] = set([result['engine']])
        result['positions'] = [position]
        #----- modified by zjn -----
        #with Lock();
        with RLock():
            self._merged_results.append(result)

    def order_results(self):
        for result in self._merged_results: 
            score = result_score(result)
            result['score'] = score
        #----- modified by zjn -----
        #with Lock();
            with RLock():
                for result_engine in result['engines']:
                    engines[result_engine].stats['score_count'] += score

        results = sorted(self._merged_results, key=itemgetter('score'), reverse=True)

        # pass 2 : group results by category and template
        gresults = []
        categoryPositions = {}

        for i, res in enumerate(results):
            # FIXME : handle more than one category per engine
            res['category'] = engines[res['engine']].categories[0]

            # FIXME : handle more than one category per engine
            category = engines[res['engine']].categories[0]\
                + ':' + res.get('template', '')\
                + ':' + ('img_src' if 'img_src' in res or 'thumbnail' in res else '')

            current = None if category not in categoryPositions\
                else categoryPositions[category]

            # group with previous results using the same category
            # if the group can accept more result and is not too far
            # from the current position

            #----- modified by zjn -----
            #and条件语句，将简单的判断条件提前
            #一旦第一个条件不满足，后几个条件将不判断
            if current is not None and (current['count'] > 0)\
                    and (len(gresults) - current['index'] < 20):
                # group with the previous results using
                # the same category with this one
                index = current['index']
                gresults.insert(index, res)

                # update every index after the current one
                # (including the current one)
                for k in categoryPositions:
                    v = categoryPositions[k]['index']
                    if v >= index:
                        categoryPositions[k]['index'] = v + 1

                # update this category
                current['count'] -= 1

            else:
                # same category
                gresults.append(res)

                # update categoryIndex
                categoryPositions[category] = {'index': len(gresults), 'count': 8}

        # update _merged_results
            self._ordered = True
            self._merged_results = gresults

    def get_ordered_results(self):
        if not self._ordered:
            self.order_results()
        return self._merged_results

    def results_length(self):
        return len(self._merged_results)

    def results_number(self):
        resultnum_sum = sum(self._number_of_results)
        if not resultnum_sum or not self._number_of_results:
            return 0
        return resultnum_sum / len(self._number_of_results)

    def add_unresponsive_engine(self, engine_error):
        self.unresponsive_engines.add(engine_error)

    def add_timing(self, engine_name, engine_time, page_load_time):
        self.timings.append({
            'engine': engines[engine_name].shortcut,
            'total': engine_time,
            'load': page_load_time
        })

    def get_timings(self):
        return self.timings
