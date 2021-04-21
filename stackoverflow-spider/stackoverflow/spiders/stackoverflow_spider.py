#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import scrapy
from stackoverflow.spiders.items import StackoverflowItem


formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('monitor')
logger.setLevel(logging.INFO)

fh = logging.FileHandler('monitor.log')
fh.setLevel(logging.INFO)

fh.setFormatter(formatter)
logger.addHandler(fh)


class StackoverflowSpider(scrapy.Spider):

    name = "stackoverflow-hadoop"

    tag = "openstack"

    index = 1

    def start_requests(self):
        _url = 'https://stackoverflow.com/questions/tagged/' + self.tag + '?page={page}&sort=votes&pagesize=50'
        urls = [_url.format(page=page) for page in range(1, 56)]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        question_list = response.xpath('//*[@class="summary"]')

        for question in question_list:
            qa_url = question.xpath('./h3/a/@href').extract()[0]
            yield scrapy.Request(url='https://stackoverflow.com' + qa_url, callback=self.parse_qa)

    def parse_qa(self, response):
        item = StackoverflowItem()

        item['index'] = self.index
        item['content'] = response.xpath('/html').extract()[0]

        self.index += 1

        yield item
