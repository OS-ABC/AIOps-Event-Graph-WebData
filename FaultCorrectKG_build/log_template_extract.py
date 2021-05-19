# 日志正则化处理后生成日志模板
import csv
import re
import json

from logparser import LogSig


# 覆盖掉日志中的时间
def remove_time(log):
    # 几种时间格式正则表达式
    time_pattern1 = re.compile("(\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2})")  # 2014-10-07 15:56:40
    time_pattern11 = re.compile("(\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2}.[0-9]+)")  # 2014-10-07 15:56:40,978 or 2014-10-07 15:56:40,978
    time_pattern2 = re.compile("(\d{2}/\d{1,2}/\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2})")  # 14/03/21 18:42:03
    time_pattern21 = re.compile("(\d{2}/\d{1,2}/\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2}.[0-9]+)")  # 14/03/21 18:42:03,221
    time_pattern3 = re.compile("(\d{1,2}:\d{1,2}:\d{1,2})")  # 09:06:44
    time_pattern31 = re.compile("(\d{1,2}:\d{1,2}:\d{1,2}.[0-9]+)")  # 09:06:44,746
    time_pattern4 = re.compile("(\w{3}\s\d{1,2},\s\d{4}\s\d{1,2}:\d{1,2}:\d{1,2}\s\w{2})")  # Dec 12, 2012 2:19:41 PM
    time_pattern41 = re.compile("(\w{3}\s\d{1,2},\s\d{4}\s\d{1,2}:\d{1,2}:\d{1,2}\s\w{2}.[0-9]+)")  # Dec 12, 2012 2:19:41 PM,223
    time_pattern5 = re.compile("(\d{1,2}\s\w{3}\s\d{4}\s\d{1,2}:\d{1,2}:\d{1,2})")  # 23 Apr 2014 15:21:28
    time_pattern51 = re.compile("(\d{1,2}\s\w{3}\s\d{4}\s\d{1,2}:\d{1,2}:\d{1,2}.[0-9]+)")  # 23 Apr 2014 15:21:28,875
    time_pattern6 = re.compile("(\w{3}\s\w{3}\s\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2}\s\w{3}\s\d{4})")  # Sat Apr 29 03:15:04 BST 2017
    time_pattern61 = re.compile("(\w{3}\s\w{3}\s\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2}\s\w{3}\s\d{4}.[0-9]+)")  # Thu Dec 24 11:18:15 GMT 2015 1450955895000
    time_pattern7 = re.compile("(GMT\+0000)")  # GMT+0000

    log = re.sub(time_pattern11, '', log)
    log = re.sub(time_pattern1, '', log)
    log = re.sub(time_pattern21, '', log)
    log = re.sub(time_pattern2, '', log)
    log = re.sub(time_pattern31, '', log)
    log = re.sub(time_pattern3, '', log)
    log = re.sub(time_pattern41, '', log)
    log = re.sub(time_pattern4, '', log)
    log = re.sub(time_pattern51, '', log)
    log = re.sub(time_pattern5, '', log)
    log = re.sub(time_pattern61, '', log)
    log = re.sub(time_pattern6, '', log)
    log = re.sub(time_pattern7, '', log)

    return log


# 覆盖掉日志中的消息级别
def remove_level(log):
    # 错误等级正则表达式
    level_words = ['ERROR', 'INFO', 'WARN', 'DEBUG', 'FATAL',
                   '[ERROR]', '[INFO]', '[WARN]', '[error]', '[info]', '[warn]',
                   'FAILED:', 'DEPRECATED:', 'Error:', 'Info:', 'Warning:']
    for word in level_words:
        log = log.replace(word, '')
    return log


# 覆盖掉日志中的组件、进程等'[]'里面的内容;以及文件名、类名等""里面的内容
def remove_other_content(log):
    pattern1 = re.compile(r'[[](.*?)[]]')
    pattern2 = re.compile(r'["](.*?)["]')

    log = re.sub(pattern1, '', log)
    log = log.replace('[]', '')
    log = re.sub(pattern2, '', log)
    log = log.replace('\"', '*')
    return log


# 日志中的ip地址、url、路径、文件、数字（含百分数）用通配符替换
def replace_content(log):
    ip_pattern = re.compile("(/|)([0-9]+\.){3}[0-9]+(:[0-9]+|)(:|)")
    path_pattern = re.compile("\s(/.+/).+?\.")
    url_pattern = re.compile("[a-z]+://(?:[-\w.]|(?:%[\da-fA-F]{2}))+")
    file_pattern = re.compile("(\/.*?\.[\w:]+)")
    number_pattern1 = re.compile("([0-9]+)")
    number_pattern2 = re.compile("([0-9]+%)")
    number_pattern3 = re.compile("([0-9]+\.[0-9]+)")

    log = re.sub(url_pattern, "*", log)
    log = re.sub(file_pattern, '*', log)
    log = re.sub(path_pattern, '*', log)
    log = re.sub(ip_pattern, '*', log)
    log = re.sub(number_pattern3, '*', log)
    log = re.sub(number_pattern2, '*', log)
    log = re.sub(number_pattern1, '*', log)

    return log


# 覆盖掉日志中所有的特殊符号
def remove_symbols(log):
    symbol_pattern = re.compile("(\.\.\.|>>>|--->|==>|=>|->|\$|>|_|~|@|-|\^|\|)")
    log = re.sub(symbol_pattern, '', log)
    return log


# 判断日志中一行是否需要删除
def is_remove_line(line):
    # 错误日志的最后一行
    end_line_pattern1 = re.compile("(\.\.\.\s[0-9]+\smore)")
    end_line_pattern2 = re.compile("(\.\.\.\s[0-9]+\selided)")

    # 含有某些特殊字符，一般为terminal操作
    symbol_line_pattern = re.compile("(\$|~|>|@|_,_)")

    # 含有任何英文字母
    word_pattern = re.compile("([a-zA-Z])")

    if re.findall(end_line_pattern1, line):
        return True
    if re.findall(end_line_pattern2, line):
        return True
    if re.findall(symbol_line_pattern, line):
        return True
    if not re.findall(word_pattern, line):  # 不包含任何英文字母的行需要删除
        return True

    return False


# 从页面抽取知识得到的csv结果文件中读取所有日志生成训练文件, 并记录最终筛选出的每一行日志原来所属的日志INDEX和页面INDEX
def get_train_log_file(knowledge_extract_result_file_path, log_train_file_output_path, log_flag_file_output_path):
    knowledge_extract_result_file = open(knowledge_extract_result_file_path, 'r')
    reader = csv.reader(knowledge_extract_result_file)

    log_train_file = open(log_train_file_output_path, 'w')

    log_count = 0
    # 记录最终筛选出的每一行日志原来所属的日志INDEX和页面INDEX
    log_flag_file = open(log_flag_file_output_path, 'w')
    log_flag_file.write('line_number ' + 'page_index ' + 'log_index' + '\n')

    for row_list in reader:
        logs = [element for element in row_list if element.find('[LOG]') == 0]
        for log_index in range(0, len(logs)):
            # 原始日志
            log = logs[log_index][5:].strip()
            # 覆盖掉日志中的时间
            log = remove_time(log)
            # 覆盖掉日志中的消息级别
            log = remove_level(log)
            # 覆盖掉'[]'和""里面的内容
            log = remove_other_content(log)
            # ip地址、url、路径、文件、数字（含百分数）用通配符替换
            log = replace_content(log)

            lines = log.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 0 and not is_remove_line(line):
                    # 覆盖掉所有的特殊符号
                    line = remove_symbols(line)
                    if len(line.replace(' ', '')) > 10:
                        log_count += 1
                        log_train_file.write(line+'\n')
                        log_flag_file.write(str(log_count) + '        ' +
                                            str(row_list[0][7:].strip()) + '        ' +
                                            str(log_index) + '\n')

    log_train_file.close()
    log_flag_file.close()
    knowledge_extract_result_file.close()


# 解析日志模板抽取结果文件，结合log_flag_file，得到每一个故障页面的每一份日志的所有日志模板
def get_result(templates_structured_file_path, log_flag_file_path, log_result_file_path, template_result_file_path):
    structured_file = open(templates_structured_file_path)
    reader = list(csv.reader(structured_file))[1:-1]
    structured_file.close()

    log_flag_file = open(log_flag_file_path)
    flags = log_flag_file.readlines()[1:-1]
    log_flag_file.close()

    log_result_dic = {}  # 记录每个故障页面处理过后的每一份日志
    template_result_dic = {}  # 记录每个故障页面的每一份日志的所有模板

    for row_list in reader:
        line_number = int(row_list[0])
        log_content = row_list[1]
        template_id = row_list[2]

        indexs = flags[line_number-1].split('        ')
        page_index = indexs[1].strip()
        log_index = indexs[2].strip()

        if page_index not in log_result_dic:
            log_result_dic[page_index] = {}
        if page_index not in template_result_dic:
            template_result_dic[page_index] = {}

        if log_index not in log_result_dic[page_index]:
            log_result_dic[page_index][log_index] = []
        if log_index not in template_result_dic[page_index]:
            template_result_dic[page_index][log_index] = []
        log_result_dic[page_index][log_index].append(log_content)
        template_result_dic[page_index][log_index].append(template_id)

    # 将最终的两个结果写入json文件
    log_result_json_file = open(log_result_file_path, 'w')
    json.dump(log_result_dic, log_result_json_file, indent=0, ensure_ascii=False)
    log_result_json_file.close()

    template_result_json_file = open(template_result_file_path, 'w')
    json.dump(template_result_dic, template_result_json_file, indent=0, ensure_ascii=False)
    template_result_json_file.close()


# 训练数据获取、日志模板抽取、结果文件解析
if __name__ == '__main__':
    knowledge_extract_result_file_path = './data/knowledge_extract_result/knowledge_extract_result.csv'

    log_data_path = './data/log_data/'
    log_train_file_name = 'log_train.log'
    log_flag_file_name = 'log_flag.txt'
    log_templates_path = log_data_path + 'log_templates/'
    log_result_file_name = 'log_result.json'
    template_result_file_name = 'template_result.json'

    # 训练数据获取
    get_train_log_file(knowledge_extract_result_file_path=knowledge_extract_result_file_path,
                       log_train_file_output_path=log_data_path + log_train_file_name,
                       log_flag_file_output_path=log_data_path + log_flag_file_name)

    # 日志模板抽取
    parser = LogSig.LogParser(indir=log_data_path,
                              outdir=log_templates_path,
                              groupNum=16,
                              log_format='<Content>',
                              rex=[])
    parser.parse(logname=log_train_file_name)

    # 获取最终结果
    get_result(templates_structured_file_path=log_templates_path + log_train_file_name + '_structured.csv',
               log_flag_file_path=log_data_path + log_flag_file_name,
               log_result_file_path=log_data_path + log_result_file_name,
               template_result_file_path=log_data_path + template_result_file_name)

