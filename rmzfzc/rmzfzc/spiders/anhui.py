# -*- coding: utf-8 -*-
import scrapy

import logging

from scrapy_splash import SplashRequest
from rmzfzc.items import rmzfzcItem

script = """
function main(splash, args)
  assert(splash:go(args.url))
  assert(splash:wait(1))
  return {
    html = splash:html(),
  }
end
"""


class AnhuiSpider(scrapy.Spider):
    name = 'anhui'
    custom_settings = {
        'SPIDER_MIDDLEWARES': {
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'utils.middlewares.MyUserAgentMiddleware.MyUserAgentMiddleware': 126,
            'utils.middlewares.DeduplicateMiddleware.DeduplicateMiddleware': 130,
            'scrapy_splash.SplashCookiesMiddleware': 140,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'ITEM_PIPELINES': {
            'utils.pipelines.MysqlTwistedPipeline.MysqlTwistedPipeline': 64,
            'utils.pipelines.DuplicatesPipeline.DuplicatesPipeline': 100,
        },
        'DUPEFILTER_CLASS': 'scrapy_splash.SplashAwareDupeFilter',
        'HTTPCACHE_STORAGE': 'scrapy_splash.SplashAwareFSCacheStorage',
        'SPLASH_URL': "http://47.106.239.73:8050/"}

    def __init__(self, pagenum=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_pagenum = pagenum

    def start_requests(self):
        try:
            contents = [
                {
                    'topic': 'szfwj',  # 省政府文件
                    'url': 'http://xxgk.ah.gov.cn/tmp/Nav_wenjian.shtml?SS_ID=11&tm=63125.92&Page=1'
                },
                {
                    'topic': 'xzgz',  # 行政规章
                    'url': 'http://xxgk.ah.gov.cn/tmp/Nav_wenjian.shtml?SS_ID=8&tm=55994.64&Page=1'
                },
                {
                    'topic': 'bmjd',  # 部门解读
                    'url': 'http://xxgk.ah.gov.cn/tmp/Nav_gongkailanmu.shtml?SS_ID=437&tm=61703.66&Page=1'
                }
            ]
            for content in contents:
                yield SplashRequest(content['url'], args={'lua_source': script, 'wait': 1}, callback=self.parse_page,
                                    cb_kwargs=content)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_page(self, response, **kwargs):
        page_count = int(self.parse_pagenum(response))
        try:
            for pagenum in range(page_count):
                if pagenum == 0:
                    url = kwargs['url']
                else:
                    url = kwargs['url'].replace(
                        'Page=1', 'Page=' + str(pagenum + 1))
                yield SplashRequest(url, args={'lua_source': script, 'wait': 1}, callback=self.parse, cb_kwargs=kwargs)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_pagenum(self, response):
        try:
            # 在解析页码的方法中判断是否增量爬取并设定爬取列表页数，如果运行
            # 脚本时没有传入参数pagenum指定爬取前几页列表页，则全量爬取
            if not self.add_pagenum:
                return int(response.css(
                    '.page_nav a:nth-child(2)::attr(href)').extract_first().split('Page=')[1])
            return self.add_pagenum
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse(self, response, **kwargs):
        if kwargs['topic'] == 'bmjd':
            for href in response.css(
                    '.xxgk_lb a[title]::attr(href)').extract():
                try:
                    url = response.urljoin(href)
                    yield scrapy.Request(url, callback=self.parse_bmjd, cb_kwargs={'url': url, 'topic': kwargs['topic']}, dont_filter=True)
                except Exception as e:
                    logging.error(self.name + ": " + e.__str__())
                    logging.exception(e)
        else:
            for href in response.css(
                    '.xxgk_lb a[onmousemove]::attr(href)').extract():
                try:
                    url = response.urljoin(href)
                    yield scrapy.Request(url, callback=self.parse_szfwj_xzgz, cb_kwargs={'url': url, 'topic': kwargs['topic']}, dont_filter=True)
                except Exception as e:
                    logging.error(self.name + ": " + e.__str__())
                    logging.exception(e)

    def parse_bmjd(self, response, **kwargs):
        try:
            item = rmzfzcItem()
            item['title'] = response.css('.sy1::text').extract_first().strip()
            item['article_num'] = response.css('.nr_topcon ul li:nth-child(6)::text').extract_first().strip()
            item['content'] = response.css('#zoom').extract_first()
            item['appendix'] = ''
            item['source'] = response.css(
                '.wzbjxx p::text').extract_first().replace('信息来源：', '')
            item['time'] = response.css('.nr_topcon ul li:nth-child(4)::text').extract_first().strip()
            item['province'] = ''
            item['city'] = ''
            item['area'] = ''
            item['website'] = '安徽省人民政府'
            item['link'] = kwargs['url']
            item['txt'] = ''.join(response.css('#zoom *::text').extract())
            item['appendix_name'] = ''
            item['module_name'] = '安徽省人民政府'
            item['spider_name'] = 'anhui'
            print(
                "===========================>crawled one item" +
                response.request.url)
        except Exception as e:
            logging.error(
                self.name +
                " in parse_item: url=" +
                response.request.url +
                ", exception=" +
                e.__str__())
            logging.exception(e)
        yield item

    def parse_szfwj_xzgz(self, response, **kwargs):
        try:
            item = rmzfzcItem()
            item['title'] = response.css('.sy1::text').extract_first().strip()
            item['article_num'] = response.css('.nr_topcon ul li:nth-child(8)::text').extract_first().strip()
            item['content'] = response.css('.wzcon').extract_first()
            item['appendix'] = ''
            item['source'] = response.css('.wzbjxx p::text').extract_first().replace('信息来源：', '')
            item['time'] = response.css('.nr_topcon ul li:nth-child(4)::text').extract_first().strip()
            item['province'] = ''
            item['city'] = ''
            item['area'] = ''
            item['website'] = '安徽省人民政府'
            item['link'] = kwargs['url']
            item['txt'] = ''.join(response.css('.wzcon *::text').extract())
            item['appendix_name'] = ''
            item['module_name'] = '安徽省人民政府'
            item['spider_name'] = 'anhui'
            print(
                "===========================>crawled one item" +
                response.request.url)
        except Exception as e:
            logging.error(
                self.name +
                " in parse_item: url=" +
                response.request.url +
                ", exception=" +
                e.__str__())
            logging.exception(e)
        yield item