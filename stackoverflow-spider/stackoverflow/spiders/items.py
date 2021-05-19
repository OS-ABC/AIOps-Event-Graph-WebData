#!/usr/bin/env python
# -*- coding: utf-8 -*-

import scrapy


class StackoverflowItem(scrapy.Item):
    index = scrapy.Field()
    content = scrapy.Field()
