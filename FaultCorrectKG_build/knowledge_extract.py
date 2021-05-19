# 筛选故障页面，并从故障页面中抽取故障描述、故障日志、故障原因和故障修复方案
import os
from bs4 import BeautifulSoup
import re
import nltk
import csv
import json
from string import punctuation


# 将一段文本切分为最短句，即在nltk切分的基础上再按照','切分
def cut_mini_sentences(text):
    mini_sentences = []
    sentences = nltk.sent_tokenize(text)
    for sentence in sentences:
        mini_sentences += sentence.split(',')
    return mini_sentences


# 对句子进行分词，去除其中的标点符号再重新组合起来，便于某些正则表达式进行判断
def process_text_for_reg_map(sentence):
    words = nltk.word_tokenize(sentence.strip(), language='english')
    words = [word for word in words if word not in punctuation]
    return ' ' + ' '.join(words) + ' '


# 读取词库中的所有词语，存到list中返回
def get_thesaurus(thesaurus_file_path):
    thesaurus_file = open(thesaurus_file_path)
    thesaurus = thesaurus_file.readlines()
    thesaurus = [word.strip().replace('_', ' ') for word in thesaurus]
    thesaurus_file.close()
    return thesaurus


# 将list中所有词语写成一条正则表达式
def get_reg_from_words(words):
    reg_text = ".*("
    for word in words:
        reg_text = reg_text + word + "|"
    reg_text = reg_text[0:-1] + ").*"
    return reg_text


# 判断句子中是否is_有触发词1+触发词2搭配
def conform_word1_word2_pattern(sentence, words1, words2):
    word1_pattern = re.compile(get_reg_from_words(words1), re.IGNORECASE)
    word2_pattern = re.compile(get_reg_from_words(words2), re.IGNORECASE)

    match_words = re.findall(word2_pattern, sentence)
    if match_words:
        for match_word in match_words:
            if re.findall(word1_pattern, process_text_for_reg_map(sentence[0:sentence.find(match_word)])):
                return True
    return False


# 判断一个页面是否是故障相关页面
def is_fault_page(title, question, thesaurus_directory_path):
    words1 = get_thesaurus(thesaurus_directory_path + 'words1.txt')
    words2 = get_thesaurus(thesaurus_directory_path + 'words2.txt')
    words3 = get_thesaurus(thesaurus_directory_path + 'words3.txt')
    words4 = get_thesaurus(thesaurus_directory_path + 'words4.txt')
    words5 = get_thesaurus(thesaurus_directory_path + 'words5.txt')
    negative_words = get_thesaurus(thesaurus_directory_path + 'negative_words.txt')

    title = process_text_for_reg_map(title)

    # 优先级1：title符合M1(出现[触发词1])
    word1_pattern = re.compile(get_reg_from_words(words1), re.IGNORECASE)
    if re.findall(word1_pattern, title):
        return True

    # 优先级2：title符合M2(出现[否定词*触发词2])
    if conform_word1_word2_pattern(title, negative_words, words2):
        return True

    # 优先级3：title符合M3(出现[触发词3])
    word3_pattern = re.compile(get_reg_from_words(words3), re.IGNORECASE)
    if re.findall(word3_pattern, title):
        return True

    sentences = cut_mini_sentences(question)  # 获取question的最短句集合

    # 优先级4：question的最短句集合符合M4(出现[触发词4*触发词5]或[触发词5*触发词4])
    for sentence in sentences:
        sentence = process_text_for_reg_map(sentence)
        if conform_word1_word2_pattern(sentence, words4, words5) or conform_word1_word2_pattern(sentence, words5, words4):
            return True

    # 优先级5：question的最短句集合符合M2(出现[否定词*触发词2])
    for sentence in sentences:
        sentence = process_text_for_reg_map(sentence)
        if conform_word1_word2_pattern(sentence, negative_words, words2):
            return True

    return False


# 判断文本text是否为日志, above_text为最接近text所在html元素的上文
def is_log(text, above_text, thesaurus_directory_path):
    words1 = get_thesaurus(thesaurus_directory_path + 'words1.txt')
    words2 = get_thesaurus(thesaurus_directory_path + 'words2.txt')
    words4 = get_thesaurus(thesaurus_directory_path + 'words4.txt')
    words5 = get_thesaurus(thesaurus_directory_path + 'words5.txt')

    text = text.replace('\n', ' ')

    # text是否符合M1(出现[触发词1]或[触发词2])
    text_m1 = False
    word1_pattern = re.compile(get_reg_from_words(words1), re.IGNORECASE)
    word2_pattern = re.compile(get_reg_from_words(words2))
    if re.findall(word1_pattern, text) or re.findall(word2_pattern, text):
        text_m1 = True

    # text是否符合M2(不出现[触发词3])
    text_m2 = False
    m2_pattern1 = re.compile(r'[{](.*?)[}]')  # 出现[{*}]
    m2_pattern2 = re.compile(r'(=)')  # 出现[=]
    if not re.findall(m2_pattern1, text) and (not re.findall(m2_pattern2, text)):
        # 出现[<*1>*</*2>]
        m2_pattern3 = re.compile(r'[<](.*?)[>]')
        contents = [content.replace('/', '') for content in re.findall(m2_pattern3, text)]  # 提取<>中的内容，并覆盖掉其中的'/'
        if len(contents) == len(set(contents)):
            text_m2 = True

    above_text = process_text_for_reg_map(above_text)

    # above_text是否符合M3(出现[触发词4])
    above_text_m3 = False
    word4_pattern = re.compile(get_reg_from_words(words4), re.IGNORECASE)
    if re.findall(word4_pattern, above_text):
        above_text_m3 = True

    # above_text是否符合M4(不出现[触发词5])
    above_text_m4 = False
    word5_pattern = re.compile(get_reg_from_words(words5), re.IGNORECASE)
    if not re.findall(word5_pattern, above_text):
        above_text_m4 = True

    if text_m1 and text_m2 and (above_text_m3 or above_text_m4):
        return True
    return False


# 提取故障修复方案文本中的所有因果句
def extract_alternative_reasons(text, thesaurus_directory_path):
    alternative_reasons = []

    words1 = get_thesaurus(thesaurus_directory_path + 'words1.txt')
    words2 = get_thesaurus(thesaurus_directory_path + 'words2.txt')

    word1_pattern = re.compile(get_reg_from_words(words1), re.IGNORECASE)
    word2_pattern = re.compile(get_reg_from_words(words2), re.IGNORECASE)

    sentences = nltk.sent_tokenize(text)  # 将text切分为句子集合
    for index in range(0, len(sentences)):
        sentence = sentences[index].strip()
        pos_result = nltk.pos_tag(nltk.word_tokenize(sentence.lower()))

        if ('since', 'IN') in pos_result:
            alternative_reasons.append(sentence)
        elif re.findall(word1_pattern, process_text_for_reg_map(sentence)):
            alternative_reasons.append(sentence)
        elif ('so', 'IN') in pos_result:
            if pos_result.index(('so', 'IN')) == 0 and index > 0:
                sentence = sentences[index - 1].strip() + ' ' + sentence
            alternative_reasons.append(sentence)
        else:
            mactch_words2 = re.findall(word2_pattern, process_text_for_reg_map(sentence))
            if mactch_words2:
                for word in mactch_words2:
                    if sentence.find(word) == 0 and index > 0:
                        sentence = sentences[index - 1].strip() + ' ' + sentence
                        break
                alternative_reasons.append(sentence)
    return alternative_reasons


# 获取最接近候选日志的上文
def get_log_above_text(log_element):
    above_text = ''
    if log_element.parent.name == 'pre' or log_element.parent.name == 'p':
        log_element = log_element.parent
    for element in log_element.previous_siblings:
        if element.name:
           above_text = element.text.strip()
           break
        else:
            text = element.strip()
            if len(text) > 0:
                above_text = text
                break
    return above_text


# 提取html元素内pre、code和blockquote标签以外的所有文本
def get_specific_text(soup):
    text = ''
    for element in soup.contents:
        if element.name:
            if element.name != 'pre' and element.name != 'code' and element.name != 'blockquote':
                text += element.text
        else:
            text += element
    return text.strip()


# 递归解析展示为一行的html元素的内容
def parse_html_to_json(element, result):
    if not element.name:
        item = {
            'type': 'text',
            'content': element,
        }
        result.append(item)
        return
    elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        item = {
            'type': 'text',
            'content': element.text,
            'title_level': element.name,
        }
        result.append(item)
        return
    elif element.name == 'strong':
        item = {
            'type': 'text',
            'content': element.text,
            'is_strong': True,
        }
        result.append(item)
        return
    elif element.name == 'code':
        item = {
            'type': 'code',
            'content': element.text,
        }
        result.append(item)
        return
    elif element.name == 'img':
        item = {
            'type': 'img',
            'src': element.get('src'),
            'alt': element.get('alt'),
        }
        result.append(item)
        return
    elif element.name == 'a':
        item = {
            'type': 'link',
            'href': element.get('href'),
            'des': element.text
        }
        result.append(item)
        return
    for sub_element in element.contents:
        parse_html_to_json(sub_element, result)


# 解析故障修复方案html元素的内容，存入字典，key值分别为text、code、image、link
def parse_answer_html_to_json(soup):
    result_dic = {}
    line_count = 0

    for element in soup.contents:
        if not element.name:
            if len(element.strip()) > 0:
                line_count += 1
                result_dic[line_count] = []
                result_dic[line_count].append({
                    'type': 'text',
                    'content': element.strip(),
                })
        else:
            try:
                if element.contents:
                    line_count += 1
                    result_dic[line_count] = []
                    parse_html_to_json(element, result_dic[line_count])
            except AttributeError:
                ''
    return result_dic


# 从故障页面中提取故障描述、日志、故障原因和故障修复方案
def knowledge_extract(input_file_path, out_file_path, thesaurus_directory_path):
    file_list = os.listdir(input_file_path)

    csv_file = open(out_file_path, "w")
    writer = csv.writer(csv_file)

    # 故障页面筛选和知识抽取用到的词典
    fault_page_select_thesaurus_path = thesaurus_directory_path + 'fault_page_select/'
    log_extract_thesaurus_path = thesaurus_directory_path + 'log_extract/'
    reason_extract_thesaurus_path = thesaurus_directory_path + 'reason_extract/'

    for page_index in range(1, len(file_list)):
        # 从html文件中提取出title和question
        print('正在处理第' + str(page_index) + '个页面')

        page_file = open(input_file_path + str(page_index) + '.html')
        page_soup = BeautifulSoup((page_file.read().strip()), 'html.parser')
        page_file.close()

        try:
            title = page_soup.find('div', {'id': 'question-header'}).find('h1').text.strip()
        except AttributeError:
            title = page_soup.find('div', {'id': 'question'}).find('h2').text.strip()

        question = page_soup.find('div', {'id': 'question'}).find('div', {'class': 's-prose js-post-body'})

        # 判断是否为故障页面
        if is_fault_page(title, get_specific_text(question), fault_page_select_thesaurus_path):
            row_data = []  # 写入csv文件的一行数据，包括从一个页面中提取的所有知识

            row_data.append('[INDEX] \n' + str(page_index))

            row_data.append('[DESCRIPTION] \n' + title)

            # 提取故障页面的tag
            try:
                tag_links = page_soup.find('div', {'class': 'grid ps-relative'}).find_all(
                    'a', {'class': 'post-tag', 'rel': 'tag'})
            except AttributeError:
                tag_links = page_soup.find('div', {'id': 'question'}).find('div', {'class': '-tags'}).find_all(
                    'a', {'class': 'post-tag'})
            tags = ''
            for tag_link in tag_links:
                tag = tag_link.text.strip()
                if tag != 'hadoop':
                    tags = tags + tag + '   '
            row_data.append('[TAGS] \n' + tags)

            # 从question中提取日志
            alternative_logs1 = question.find_all('code')
            alternative_logs2 = question.find_all('blockquote')

            for log in alternative_logs1:
                log_text = log.text.strip()
                if is_log(log_text, get_log_above_text(log), log_extract_thesaurus_path):
                    row_data.append('[LOG] \n' + log_text)

            for log in alternative_logs2:
                log_text = log.text.strip()
                if is_log(log_text, get_log_above_text(log), log_extract_thesaurus_path):
                    row_data.append('[LOG] \n' + log_text)

            # 提取所有的故障修复方案
            try:
                answers = page_soup.find('div', {'id': 'answers'}).find_all('div', {'class': 's-prose js-post-body'})
                votes = page_soup.find('div', {'id': 'answers'}).find_all('div', {'itemprop': 'upvoteCount'})
            except AttributeError:
                answers = []
                votes = []
                answer_soups = page_soup.find_all('div', {'class': '-summary answer'})
                for answer_soup in answer_soups:
                    answers.append(answer_soup.find('div', {'class': 's-prose js-post-body'}))
                    votes.append(answer_soup.find('span', {'itemprop': 'upvoteCount'}))

            for answer_index in range(0, len(answers)):
                answer_soup = answers[answer_index]
                # 从每个故障修复方案文本中提取出可能原因
                alternative_reasons = extract_alternative_reasons(get_specific_text(answer_soup),
                                                                  reason_extract_thesaurus_path)

                solution_html = ''
                for element in answer_soup.contents:
                    solution_html += str(element)

                row_data.append('[REASON] \n' + json.dumps({'value': alternative_reasons}))
                row_data.append('[SOLUTION-HTML] \n' + solution_html.strip())
                row_data.append('[SOLUTION-JSON] \n' + json.dumps(parse_answer_html_to_json(answer_soup),
                                                                  indent=0, ensure_ascii=False))
                row_data.append('[VOTE] \n' + votes[answer_index].text.strip())

            writer.writerow(row_data)
    csv_file.close()


if __name__ == '__main__':
    knowledge_extract(input_file_path='./data/stackoverflow_hadoop_pages/',
                      out_file_path='./data/knowledge_extract_result/knowledge_extract_result.csv',
                      thesaurus_directory_path='./data/thesaurus/')
