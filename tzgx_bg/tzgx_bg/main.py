# -*- coding: utf-8 -*-import sys,osfrom scrapy.cmdline import executesys.path.append(os.path.abspath(os.path.dirname(__file__)))sys.path.append(os.path.abspath(os.path.dirname(__file__)+"/../"))execute("scrapy crawl tzgx_bg_xtw".split())