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


class TianJinSzfwjSpider(scrapy.Spider):
    name = 'heilongjiang'
    custom_settings = {
        'SPIDER_MIDDLEWARES': {
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'utils.middlewares.MyUserAgentMiddleware.MyUserAgentMiddleware': 126,
            'utils.middlewares.DeduplicateMiddleware.DeduplicateMiddleware': 130,
        },
        'ITEM_PIPELINES': {
            'utils.pipelines.MysqlTwistedPipeline.MysqlTwistedPipeline': 64,
            'utils.pipelines.DuplicatesPipeline.DuplicatesPipeline': 100,
        },
        'DUPEFILTER_CLASS': 'scrapy_splash.SplashAwareDupeFilter',
        'HTTPCACHE_STORAGE': 'scrapy_splash.SplashAwareFSCacheStorage',
        'SPLASH_URL': 'http://localhost:8050/'}

    def __init__(self, pagenum=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_pagenum = pagenum

    def start_requests(self):
        try:
            contents = [
                {
                    'url': 'http://www.hlj.gov.cn/zwfb/zcjd/',
                    'topic': 'zcjd'
                },
                {
                    'url': 'http://www.hlj.gov.cn/zwfb/zfgz/',
                    'topic': 'zfgz'
                }
            ]
            for content in contents:
                yield SplashRequest(content['url'], args={'lua_source': script, 'wait': 1}, callback=self.parse_page,cb_kwargs=content)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_page(self, response,**kwargs):
        page_count = int(self.parse_pagenum(response)) + 2
        temp = response.xpath('//*[@class="fanye1"]/a/@href').extract_first()
        temp = temp[:temp.find('_')+1]
        try:
            # 在解析翻页数之前，首先解析首页内容
            for pagenum in range(page_count):
                if pagenum > 0:
                    url = temp + str(pagenum).zfill(8) +'.shtml'
                    print(url)
                    yield SplashRequest(url, args={'lua_source': script, 'wait': 1}, callback=self.parse, dont_filter=True,cb_kwargs=kwargs)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_pagenum(self, response):
        try:
            # 在解析页码的方法中判断是否增量爬取并设定爬取列表页数，如果运行
            # 脚本时没有传入参数pagenum指定爬取前几页列表页，则全量爬取
            if not self.add_pagenum:
                self.add_pagenum = response.xpath('//*[@class="fanye1"]/a/@href').re(r'([1-9]\d*?\d*)')[2]
            return self.add_pagenum
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse(self, response,**kwargs):
        for href in response.xpath('//div[@class="li-left hei"]/span/a/@href'):
            try:
                yield scrapy.Request(href.extract(),callback=self.parse_item, dont_filter=True,cb_kwargs=kwargs)
            except Exception as e:
                logging.error(self.name + ": " + e.__str__())
                logging.exception(e)
        # 处理翻页
        # 1. 获取翻页链接
        # 2. yield scrapy.Request(第二页链接, callback=self.parse, dont_filter=True)

    def parse_item(self, response,**kwargs):
        try:
            item = rmzfzcItem()
            item['title'] = response.xpath('//*[@class="tm2"]/text()').extract_first()
            item['article_num'] = ''
            item['content'] = "".join(response.xpath('//div[@class="nr5"]').extract())
            if kwargs['topic'] == 'zcjd':
                item['source'] = "".join(response.xpath('//*[@class="tm3"]/span[2]//text()').extract()).replace('来源：','')
                item['time'] = "".join(response.xpath('//*[@class="tm3"]/span[1]//text()').extract()).replace('时间：','')
            else:
                item['source'] = ''
                item['time'] = "".join(response.xpath('//*[@class="tm3"]/span[2]//text()').extract()).replace('发文时间：', '')
            item['province'] = '黑龙江省'
            item['city'] = ''
            item['area'] = ''
            item['website'] = '黑龙江省人民政府'
            item['module_name'] = '黑龙江省人民政府-部门解读'
            item['spider_name'] = 'heilongjiang_'+kwargs['topic']
            item['txt'] = "".join(response.xpath('//div[@class="nr5"]//text()').extract())
            item['appendix_name'] = ''
            item['link'] = response.request.url
            item['appendix'] = ''
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