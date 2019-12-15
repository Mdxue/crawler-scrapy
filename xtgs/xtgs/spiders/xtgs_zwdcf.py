# -*- coding: utf-8 -*-
import scrapy
import logging

from scrapy_splash import SplashRequest
from xtgs.items import xtgsItem
from utils.tools.attachment import get_times

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
    name = 'xtgs_zwdcf'
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
        'SPLASH_URL': "http://47.106.239.73:8050/"}

    def __init__(self, pagenum=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_pagenum = pagenum

    def start_requests(self):
        try:
            url = "http://www.zhongwentouzi.com/list-34-1.html"
            yield SplashRequest(url, args={'lua_source': script, 'wait': 1}, callback=self.parse)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_page(self, response):
        page_count = int(self.parse_pagenum(response))
        print(page_count)
        try:
            for pagenum in range(page_count):
                if pagenum > 0:
                    url = 'http://www.suobuy.com/xintuo/' + str(pagenum) + '.html' if pagenum > 1 else "http://www.suobuy.com/xintuo/index.html"
                    yield SplashRequest(url, args={'lua_source': script, 'wait': 1}, callback=self.parse, dont_filter=True)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_pagenum(self, response):
        try:
            # 在解析页码的方法中判断是否增量爬取并设定爬取列表页数，如果运行
            # 脚本时没有传入参数pagenum指定爬取前几页列表页，则全量爬取
            if not self.add_pagenum:
                return int(response.xpath('//*[@class="pages"]/a[last()-1]/text()').extract_first()) + 1
            return self.add_pagenum
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse(self, response):
        for href in response.xpath('//li[@class="caoz"]/a/@href').extract():
            try:
                print(href)
                yield SplashRequest(href,callback=self.parse_item, dont_filter=True)
            except Exception as e:
                logging.error(self.name + ": " + e.__str__())
                logging.exception(e)
        # 处理翻页
        # 1. 获取翻页链接
        # 2. yield scrapy.Request(第二页链接, callback=self.parse, dont_filter=True)

    def parse_item(self, response,**kwargs):
        try:
            item = xtgsItem()
            name = response.xpath('//div[@class="product-show-item"][1]/table/tr[1]/td[2]/text()').extract_first()
            simple_name = response.xpath('//div[@class="product-show-item"][1]/table/tr[2]/td[2]/text()').extract_first()
            en_name = response.xpath('//div[@class="product-show-item"][1]/table/tr[3]/td[2]/text()').extract_first()
            create_date = response.xpath('//div[@class="product-show-item"][1]/table/tr[4]/td[2]/text()').extract_first()
            registe_money = response.xpath('//div[@class="product-show-item"][1]/table/tr[4]/td[4]/text()').extract_first()
            address = response.xpath('//div[@class="product-show-item"][1]/table/tr[5]/td[2]/text()').extract_first()
            legal_person = response.xpath('//div[@class="product-show-item"][1]/table/tr[5]/td[4]/text()').extract_first()
            company_type = response.xpath('//div[@class="product-show-item"][1]/table/tr[6]/td[2]/text()').extract_first()
            is_ipo = response.xpath('//div[@class="product-show-item"][1]/table/tr[6]/td[4]/text()').extract_first()
            shareholder = response.xpath('//div[@class="product-show-item"][1]/table/tr[7]/td[2]/text()').extract_first()
            company_intro = ''.join(response.xpath('//*[@id="pc"]/div/div[3]/div[2]/div/div/div[2]/div/div[2]/div//text()').extract())
            aum = response.xpath('//*[@id="pc"]/div/div[3]/div[2]/div/div/div[1]/div/div/div[1]/div/div[3]/h3/span/text()').extract_first()

            item['name'] = name  # 公司名称
            item['simple_name'] = simple_name  # 公司简称
            item['en_name'] = en_name  # 英文名称
            item['create_date'] = get_times(create_date)  # 成立日期
            item['address'] = address  # 所在地
            item['registe_money'] = registe_money  # 注册资本
            item['is_ipo'] = is_ipo  # 是否上市
            item['company_type'] = company_type  # 公司类型
            item['regist_address'] = ''  # 注册地址
            item['partner_compose'] = ''  # 股东构成
            item['partner_bg'] = ''  # 股东背景
            item['company_intro'] = company_intro.replace('\xa0','') if company_intro else ''  # 公司简介
            item['legal_person'] = legal_person  # 法人代表
            item['dongshizhang'] = ''  # 董事长
            item['shareholder'] = shareholder  # 大股东
            item['general_manager'] = ''  # 总经理
            item['aum'] = aum  # 资产管理规模
            item['avg_yield'] = ''  # 平均收益率
            item['pro_hold_rate'] = ''  # 产品兑付比例
            item['company_website'] = ''  # 公司网址
            item['telephone'] = ''  # 电话
            item['fax'] = ''  # 传真
            item['postcode'] = ''  # 邮编
            item['website'] = '中稳定财富'  # 数据来源网站
            item['link'] = response.request.url  # 数据源链接
            item['spider_name'] = 'xtgs_zwdcf'  # 名称
            item['module_name'] = '信托公司_中稳定财富'  # 模块名称

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
