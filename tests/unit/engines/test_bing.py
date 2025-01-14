# -*- coding: utf-8 -*-
from collections import defaultdict
import mock
from searx.engines import bingcn
from searx.testing import SearxTestCase


class TestbingcnEngine(SearxTestCase):

    def test_request(self):
        bingcn.supported_languages = ['en', 'fr', 'zh-CHS', 'zh-CHT', 'pt-PT', 'pt-BR']
        query = u'test_query'
        dicto = defaultdict(dict)
        dicto['pageno'] = 1
        dicto['language'] = 'fr-FR'
        params = bingcn.request(query.encode('utf-8'), dicto)
        self.assertTrue('url' in params)
        self.assertTrue(query in params['url'])
        self.assertTrue('language%3AFR' in params['url'])
        self.assertTrue('bing.com' in params['url'])

        dicto['language'] = 'all'
        params = bingcn.request(query.encode('utf-8'), dicto)
        self.assertTrue('language' in params['url'])

    def test_response(self):
        dicto = defaultdict(dict)
        dicto['pageno'] = 1
        dicto['language'] = 'fr-FR'
        self.assertRaises(AttributeError, bingcn.response, None)
        self.assertRaises(AttributeError, bingcn.response, [])
        self.assertRaises(AttributeError, bingcn.response, '')
        self.assertRaises(AttributeError, bingcn.response, '[]')

        response = mock.Mock(text='<html></html>')
        response.search_params = dicto
        self.assertEqual(bingcn.response(response), [])

        response = mock.Mock(text='<html></html>')
        response.search_params = dicto
        self.assertEqual(bingcn.response(response), [])

        html = """
        <div>
            <div id="b_tween">
                <span class="sb_count" data-bm="4">23 900 000 résultats</span>
            </div>
            <ol id="b_results" role="main">
                <div class="sa_cc" u="0|5109|4755453613245655|UAGjXgIrPH5yh-o5oNHRx_3Zta87f_QO">
                    <div Class="sa_mc">
                        <div class="sb_tlst">
                            <h3>
                                <a href="http://this.should.be.the.link/" h="ID=SERP,5124.1">
                                <strong>This</strong> should be the title</a>
                            </h3>
                        </div>
                        <div class="sb_meta"><cite><strong>this</strong>.meta.com</cite>
                            <span class="c_tlbxTrg">
                                <span class="c_tlbxH" H="BASE:CACHEDPAGEDEFAULT" K="SERP,5125.1">
                                </span>
                            </span>
                        </div>
                        <p><strong>This</strong> should be the content.</p>
                    </div>
                </div>
            </ol>
        </div>
        """
        response = mock.Mock(text=html)
        response.search_params = dicto
        results = bingcn.response(response)
        self.assertEqual(type(results), list)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'This should be the title')
        self.assertEqual(results[0]['url'], 'http://this.should.be.the.link/')
        self.assertEqual(results[0]['content'], 'This should be the content.')
        self.assertEqual(results[-1]['number_of_results'], 23900000)

        html = """
        <div>
            <div id="b_tween">
                <span class="sb_count" data-bm="4">9-18 résultats sur 23 900 000</span>
            </div>
            <ol id="b_results" role="main">
                <li class="b_algo" u="0|5109|4755453613245655|UAGjXgIrPH5yh-o5oNHRx_3Zta87f_QO">
                    <div Class="sa_mc">
                        <div class="sb_tlst">
                            <h2>
                                <a href="http://this.should.be.the.link/" h="ID=SERP,5124.1">
                                <strong>This</strong> should be the title</a>
                            </h2>
                        </div>
                        <div class="sb_meta"><cite><strong>this</strong>.meta.com</cite>
                            <span class="c_tlbxTrg">
                                <span class="c_tlbxH" H="BASE:CACHEDPAGEDEFAULT" K="SERP,5125.1">
                                </span>
                            </span>
                        </div>
                        <p><strong>This</strong> should be the content.</p>
                    </div>
                </li>
            </ol>
        </div>
        """
        dicto['pageno'] = 2
        response = mock.Mock(text=html)
        response.search_params = dicto
        results = bingcn.response(response)
        self.assertEqual(type(results), list)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'This should be the title')
        self.assertEqual(results[0]['url'], 'http://this.should.be.the.link/')
        self.assertEqual(results[0]['content'], 'This should be the content.')
        self.assertEqual(results[-1]['number_of_results'], 23900000)

        html = """
        <div>
            <div id="b_tween">
                <span class="sb_count" data-bm="4">23 900 000 résultats</span>
            </div>
            <ol id="b_results" role="main">
                <li class="b_algo" u="0|5109|4755453613245655|UAGjXgIrPH5yh-o5oNHRx_3Zta87f_QO">
                    <div Class="sa_mc">
                        <div class="sb_tlst">
                            <h2>
                                <a href="http://this.should.be.the.link/" h="ID=SERP,5124.1">
                                <strong>This</strong> should be the title</a>
                            </h2>
                        </div>
                        <div class="sb_meta"><cite><strong>this</strong>.meta.com</cite>
                            <span class="c_tlbxTrg">
                                <span class="c_tlbxH" H="BASE:CACHEDPAGEDEFAULT" K="SERP,5125.1">
                                </span>
                            </span>
                        </div>
                        <p><strong>This</strong> should be the content.</p>
                    </div>
                </li>
            </ol>
        </div>
        """
        dicto['pageno'] = 33900000
        response = mock.Mock(text=html)
        response.search_params = dicto
        results = bingcn.response(response)
        self.assertEqual(bingcn.response(response), [])

    def test_fetch_supported_languages(self):
        html = """<html></html>"""
        response = mock.Mock(text=html)
        results = bingcn._fetch_supported_languages(response)
        self.assertEqual(type(results), list)
        self.assertEqual(len(results), 0)

        html = """
        <html>
            <body>
                <form>
                    <div id="limit-languages">
                        <div>
                            <div><input id="es" value="es"></input></div>
                        </div>
                        <div>
                            <div><input id="pt_BR" value="pt_BR"></input></div>
                            <div><input id="pt_PT" value="pt_PT"></input></div>
                        </div>
                    </div>
                </form>
            </body>
        </html>
        """
        response = mock.Mock(text=html)
        languages = bingcn._fetch_supported_languages(response)
        self.assertEqual(type(languages), list)
        self.assertEqual(len(languages), 3)
        self.assertIn('es', languages)
        self.assertIn('pt-BR', languages)
        self.assertIn('pt-PT', languages)
