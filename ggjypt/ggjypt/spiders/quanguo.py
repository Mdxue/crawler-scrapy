# -*- coding: utf-8 -*-
import scrapy
import logging

from scrapy_splash import SplashRequest
from ggjypt.items import ztbkItem
import time
from utils.tools.attachment import get_attachments,get_times

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
  assert(splash:wait(0.5))
  wait_for_element(splash, ".btn")
  splash:runjs("document.querySelector('#choose_time_05').click()")
  splash:runjs("document.querySelector('#searchButton').click()")
  wait_for_element(splash, ".btn")
  js = string.format("document.querySelector('#gotopage').value =%d", args.page)
  splash:evaljs(js)
  splash:runjs("document.querySelector('#toview').innerHTML=''")
  splash:runjs("document.querySelector('.btn').click()")
  wait_for_element(splash, "#toview > div")
  return splash:html()
end
"""

class GansuSpider(scrapy.Spider):
    name = 'quanguo_ggjypt'
    custom_settings = {
        'CONCURRENT_REQUESTS': 10,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 10,
        'CONCURRENT_REQUESTS_PER_IP': 0,
        'DOWNLOAD_DELAY': 0.5,
        'DOWNLOADER_MIDDLEWARES' : {
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'SPIDER_MIDDLEWARES' : {
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
        'DUPEFILTER_CLASS': 'scrapy_splash.SplashAwareDupeFilter',
        'HTTPCACHE_STORAGE' : 'scrapy_splash.SplashAwareFSCacheStorage',
        'ITEM_PIPELINES': {
            'utils.pipelines.MysqlTwistedPipeline.MysqlTwistedPipeline': 64,
            'utils.pipelines.DuplicatesPipeline.DuplicatesPipeline': 100,
        },
        'SPLASH_URL': "http://localhost:8050/"}

    def __init__(self, pagenum=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_pagenum = pagenum

    def start_requests(self):
        try:
            contents = [
                {
                    'topic': 'quanguo',  # 全国公共资源拍卖交易网
                    'url': 'http://deal.ggzy.gov.cn/ds/deal/dealList.jsp'
                }
            ]
            for content in contents:
                yield SplashRequest(content['url'],
                                    endpoint = 'execute',
                                    args={
                                        'lua_source': script,
                                        'wait': 1,
                                        'page': 1,
                                        'url': content['url'],
                                    },
                                    callback=self.parse_page,
                                    cb_kwargs=content)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_page(self, response, **kwargs):
        page_count = int(self.parse_pagenum(response))
        print('page_count' + str(page_count))
        try:
            for pagenum in range(page_count):
                if pagenum > 0:
                    yield SplashRequest(kwargs['url'],
                                        endpoint='execute',
                                        args={
                                            'lua_source': script,
                                            'wait': 1,
                                            'page': pagenum,
                                            'url': kwargs['url'],
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
            if not self.add_pagenum:
                return int(response.xpath('//*[@class="count"]').re(r'([1-9]\d*\.?\d*)')[1]) + 1
            return self.add_pagenum
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)
    def parse(self, response, **kwargs):
        script = """
        function main(splash, args)
          splash:go(args.url)
          assert(splash:wait(1))
          splash:runjs("document.querySelector('body').innerHTML = document.getElementsByTagName('iframe')[0].contentWindow.document.body.querySelector('.detail').innerHTML")
          return splash:html()
        end
        """
        for selector in response.xpath('//*[@class="publicont"]/div/h4'):
            try:
                item = {}
                item['title'] = selector.xpath('./a/text()').extract_first()
                item['time'] = selector.xpath('./span/text()').extract_first()
                url = selector.xpath('./a/@href').extract_first()
                item['url'] = url
                yield SplashRequest(url,
                    endpoint='execute',
                    args={
                        'lua_source': script,
                        'wait': 1,
                        'url': url,
                    },
                    callback=self.parse_item,
                    cb_kwargs=item)
            except Exception as e:
                logging.error(self.name + ": " + e.__str__())
                logging.exception(e)

    def parse_item(self, response, **kwargs):
        if kwargs['title']:
            try:
                appendix, appendix_name = get_attachments(response)
                category = '其他';
                title = kwargs['title']
                if title.find('招标') >= 0:
                    category = '招标'
                elif title.find('中标') >= 0:
                    category = '中标'
                elif title.find('成交') >= 0:
                    category = '成交'
                elif title.find('结果') >= 0:
                    category = '结果'
                elif title.find('单一') >= 0:
                    category = '单一'
                item = ztbkItem()
                item['title'] = title
                item['content'] = "".join(response.xpath('//div[@id="mycontent"]').extract())
                item['source'] = response.xpath('//a[@class="originUrl"]/text()').extract_first()
                item['category'] = category
                item['type'] = ''
                item['region'] = '全国'
                item['time'] = kwargs['time']
                item['website'] = '全国公共资源交易服务平台'
                item['module_name'] = '全国-公共交易平台'
                item['spider_name'] = 'quanguo_ggjypt'
                item['txt'] = "".join(response.xpath('//div[@id="mycontent"]//text()').extract())
                item['appendix_name'] = appendix_name
                item['link'] = kwargs['url']
                item['appendix'] = appendix
                item['time'] = get_times(item['time'])
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