# 对抽取到的故障修复方案进行校验
import nltk


# 读取词库中的所有词语放入list中
def get_word_list(thesaurus_file_path):
    thesaurus_file = open(thesaurus_file_path, 'r')
    words = [word.strip() for word in thesaurus_file.readlines()]
    thesaurus_file.close()
    return words


# 根据vote数量和关键词对故障修复方案进行校验
# 输入为一个solution_json和该answer获得的vote数量
# 可以在图谱存储时再调用该方法
def solution_verify(solution_json, vote, instructions_path='./data/knowledge_verify/instructions.txt',
                    config_file_path='./data/knowledge_verify/config_files.txt'):
    if vote < 0:
        return False

    instructions = get_word_list(instructions_path)
    config_files = get_word_list(config_file_path)

    for line_number in solution_json:
        line_list = solution_json[line_number]
        for element_dic in line_list:
            if element_dic['type'] == 'code':
                return True
            elif element_dic['type'] == 'text':
                text = element_dic['content']
                words = nltk.word_tokenize(text.lower())
                if set(words).intersection(set(instructions)):
                    return True
                if set(words).intersection(set(config_files)):
                    return True
    return False


