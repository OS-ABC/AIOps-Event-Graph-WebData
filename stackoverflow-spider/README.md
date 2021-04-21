# 爬取stackoverflow中某一tag下的所有Q&A页面

## 项目目录结构
1.data目录存放爬取的所有页面
```
例：./data/hadoop/中存放stackoverflow中tag为hadoop的所有页面
```
2、stackoverflow目录为爬虫框架，具体说明如下：
```
./stackoverflow/spiders/stackoverflow_spiders.py: 
爬虫主程序；通过指定tag值来爬取某一tag下的所有页面，当前tag为hadoop;
注意：stackoverflow页面结构可能会发生变化，可能需要根据当下实际结构修改解析函数parse的实现
```
```
./stackoverflow/pipelines.py: 
处理每个爬取的页面的程序；每个页面按照序号命名并以html文件的格式存储在相应的位置
```
## 项目运行
1.在命令行将当前路径切换至当前项目的spiders目录下

2.命令行spiders目录下运行命令：
```
scrapy crawl stackoverflow-hadoop
其中stackoverflow-hadoop为爬虫项目名，与spiders/stackoverflow_spiders.py中指定的name一致
```