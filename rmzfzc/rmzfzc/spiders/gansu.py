# -*- coding: utf-8 -*-
import scrapy

import logging
from scrapy_splash import SplashRequest
from rmzfzc.items import rmzfzcItem
import time

class shandongZfwjSpider(scrapy.Spider):
    name = 'gansu'
    custom_settings = {
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'SPIDER_MIDDLEWARES': {
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
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
        script = """
        function wait_for_element(splash, css, maxwait)
          -- Wait until a selector matches an element
          -- in the page. Return an error if waited more
          -- than maxwait seconds.
          if maxwait == nil then
              maxwait = 10
          end
          return splash:wait_for_resume(string.format([[
            function main(splash) {
              var selector = '%s';
              var maxwait = %s;
              var end = Date.now() + maxwait*1000;

              function check() {
                if(document.querySelector(selector)) {
                  splash.resume('Element found');
                } else if(Date.now() >= end) {
                  var err = 'Timeout waiting for element';
                  splash.error(err + " " + selector);
                } else {
                  setTimeout(check, 200);
                }
              }
              check();
            }
          ]], css, maxwait))
        end
        function main(splash, args)
          splash:go(args.url)
          wait_for_element(splash, ".default_pgContainer")
          splash:wait(1)
          return splash:html()
        end
        """
        try:
            contents = [
                {
                    'topic': 'zcwj',  # 政策文件
                    'url': 'http://www.gansu.gov.cn/col/col4729/index.html'
                },
                {
                    'topic': 'zcjd',  # 政策解读
                    'url': 'http://www.gansu.gov.cn/col/col4745/index.html'
                }
            ]
            for content in contents:
                yield SplashRequest(content['url'],
                                    endpoint='execute',
                                    args={
                                        'lua_source': script,
                                        'wait': 1,
                                        'url': content['url'],
                                    },
                                    callback=self.parse_page,
                                    cb_kwargs=content)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_page(self, response, **kwargs):
        script = """
        function wait_for_element(splash, css, maxwait)
          -- Wait until a selector matches an element
          -- in the page. Return an error if waited more
          -- than maxwait seconds.
          if maxwait == nil then
              maxwait = 10
          end
          return splash:wait_for_resume(string.format([[
            function main(splash) {
              var selector = '%s';
              var maxwait = %s;
              var end = Date.now() + maxwait*1000;

              function check() {
                if(document.querySelector(selector)) {
                  splash.resume('Element found');
                } else if(Date.now() >= end) {
                  var err = 'Timeout waiting for element';
                  splash.error(err + " " + selector);
                } else {
                  setTimeout(check, 200);
                }
              }
              check();
            }
          ]], css, maxwait))
        end
        function main(splash, args)
          splash:go(args.url)
          wait_for_element(splash, "#pages")
          js = string.format("document.querySelector('.default_pgCurrentPage').value =%s", args.page)
          splash:evaljs(js)
          assert(splash:wait(0.1))
          splash:runjs("document.querySelector('.default_pgContainer').innerHTML = ''")
          assert(splash:wait(0.1))
          splash:runjs("document.querySelector('.go-button').click()")
          assert(splash:wait(0.1))
          return splash:html()
        end
        """
        page_count = int(self.parse_pagenum(response)) + 1
        print('page_count' + str(page_count))
        try:
            for pagenum in range(page_count):
                if pagenum > 0:
                    time.sleep(0.5)
                    url = kwargs['url']
                    yield SplashRequest(url,
                                        endpoint='execute',
                                        args={
                                            'lua_source': script,
                                            'wait': 1,
                                            'url': url,
                                        },
                                        callback=self.parse,
                                        cb_kwargs=kwargs)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_pagenum(self, response):
        try:
            # 在解析页码的方法中判断是否增量爬取并设定爬取列表页数，如果运行
            # 脚本时没有传入参数pagenum指定爬取前几页列表页，则全量爬取
            return response.xpath('//*[@class="default_pgTotalPage"]/text()').extract_first()
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse(self, response, **kwargs):
        for selector in response.xpath('//*[@id="_fill"]/tbody/tr'):
            try:
                item = {}
                item['title'] = selector.xpath('./td[2]/a/text()').extract_first()
                item['time'] = selector.xpath('./td[4]/text()').extract_first()
                item['article_num'] = selector.xpath('./td[2]/div/ul/li[6]/text()').extract_first()
                item['source'] = selector.xpath('./td[3]/text()').extract_first()
                url = selector.xpath('./td[2]/a/@href').extract_first()
                if url:
                    print('url==='+url)
                    yield scrapy.Request(url,callback=self.parse_item, dont_filter=True, cb_kwargs=item)
            except Exception as e:
                logging.error(self.name + ": " + e.__str__())
                logging.exception(e)

    def parse_item(self, response, **kwargs):
        try:
            if kwargs['title']:
                item = rmzfzcItem()
                item['title'] = kwargs['title']
                item['article_num'] = kwargs['article_num']
                item['content'] = "".join(response.xpath('//*[@class="zwnr"]').extract())
                item['appendix'] = ''
                item['source'] = kwargs['source']
                item['time'] = kwargs['time']
                item['province'] = ''
                item['city'] = ''
                item['area'] = ''
                item['website'] = '山东省人民政府'
                item['module_name'] = '山东省人民政府-政策解读'
                item['spider_name'] = 'shandong_zfwj'
                item['txt'] = "".join(response.xpath('//*[@class="zwnr"]//text()').extract())
                item['appendix_name'] = ''
                item['link'] = response.request.url
                print("===========================>crawled one item" +
                    response.request.url)
        except Exception as e:
            logging.error(self.name + " in parse_item: url=" + response.request.url + ", exception=" + e.__str__())
            logging.exception(e)
        yield item