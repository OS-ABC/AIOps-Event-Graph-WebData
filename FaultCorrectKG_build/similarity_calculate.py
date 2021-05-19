import csv
import json
import jieba
from string import punctuation
import re
from gensim.models import word2vec
import numpy as np
from scipy.spatial.distance import pdist
from sklearn.feature_extraction.text import CountVectorizer
from scipy.linalg import norm


# 使用jieba对句子分词，并去掉特殊符号全部转化为小写后转化成字符串输出
def cut_sentence_process(sentence):
    words = jieba.cut(re.sub('\W+', ' ', sentence))
    result = ''
    for word in words:
        word = word.strip()
        if len(word) > 0 and word not in punctuation:
            result += word.lower() + ' '
    return result.strip()


# 从页面抽取知识得到的csv结果文件中读取所有的故障描述，然后分词生成训练文件
def get_description_train_file(knowledge_extract_result_file_path, train_file_output_path):
    knowledge_extract_result_file = open(knowledge_extract_result_file_path, 'r')
    reader = csv.reader(knowledge_extract_result_file)

    description_train_file = open(train_file_output_path, 'w')

    for row_list in reader:
        description = row_list[1][13:].strip()
        if len(description) > 0:
            description_train_file.write(cut_sentence_process(description)+'\n')
    description_train_file.close()
    knowledge_extract_result_file.close()


# 从页面抽取知识得到的csv结果文件中读取所有的故障原因，然后分词生成训练文件
def get_reason_train_file(knowledge_extract_result_file_path, train_file_output_path):
    knowledge_extract_result_file = open(knowledge_extract_result_file_path, 'r')
    reader = csv.reader(knowledge_extract_result_file)

    reason_train_file = open(train_file_output_path, 'w')

    for row_list in reader:
        reasons = [element for element in row_list if element.find('[REASON]') == 0]
        for reason in reasons:
            alternative_reasons = json.loads(reason[8:].strip())['value']
            for alternative_reason in alternative_reasons:
                reason_train_file.write(cut_sentence_process(alternative_reason) + '\n')

    knowledge_extract_result_file.close()

    reason_train_file.close()


# word2vec模型训练
def train_word2vec_model(train_file_path, model_output_path, size=200):
    # 获取训练数据集
    train_file = open(train_file_path)
    sentences = train_file.readlines()

    x_train = []

    for sentence in sentences:
        word_list = sentence.strip().split(' ')
        for i in range(0, len(word_list)):
            word_list[i] = word_list[i].strip()
        x_train.append(word_list)

    model = word2vec.Word2Vec(x_train, sg=1, size=size, window=3, min_count=1, workers=4)
    model.save(model_output_path)
    model.wv.save_word2vec_format(model_output_path+'_format')  # 顺便保存一份可视化模型以便人工查看

    train_file.close()


# 根据word2Vec模型获取句子向量
def get_vec(model, sentence, size=200):
    model = word2vec.Word2Vec.load(model)

    words = cut_sentence_process(sentence).strip().split(' ')

    sentence_vec = np.zeros(size)
    sentence_word_length = 0

    for word in words:
        try:
            sentence_vec += model[word]
        except KeyError:
            sentence_vec += np.zeros(size)
        sentence_word_length += 1

    if sentence_word_length > 0:
        sentence_vec /= sentence_word_length

    return sentence_vec


# 完成训练数据获取以及模型训练的全过程
if __name__ == '__main__':
    knowledge_extract_result_file_path = './data/knowledge_extract_result/knowledge_extract_result.csv'

    train_file_output_dir = './data/similarity_calculate_data/'
    description_train_file_name = 'description_train.txt'
    description_train_file = train_file_output_dir + description_train_file_name
    reason_train_file_name = 'reason_train.txt'
    reason_train_file = train_file_output_dir + reason_train_file_name

    model_output_dir = './data/similarity_calculate_data/word2vec_model/'
    description_model_name = 'description_model'
    description_model = model_output_dir + description_model_name
    reason_model_name = 'reason_model'
    reason_model = model_output_dir + reason_model_name

    get_description_train_file(knowledge_extract_result_file_path=knowledge_extract_result_file_path,
                               train_file_output_path=description_train_file)

    get_reason_train_file(knowledge_extract_result_file_path=knowledge_extract_result_file_path,
                          train_file_output_path=reason_train_file)

    train_word2vec_model(train_file_path=description_train_file,
                         model_output_path=description_model)

    train_word2vec_model(train_file_path=reason_train_file,
                         model_output_path=reason_model)


# 计算两个句子向量的相似度 sentence_type取0代表故障描述,取1代故障原因
def word2vec_sim_cal(model, sentence1, sentence2):
    sentence1_vec = get_vec(model, sentence1)
    sentence2_vec = get_vec(model, sentence2)

    cosine = pdist([sentence1_vec, sentence2_vec], 'euclidean')
    euclidean = pdist([sentence1_vec, sentence2_vec], 'cosine')
    jaccard = pdist([sentence1_vec, sentence2_vec], 'jaccard')

    dis = float((cosine + euclidean + jaccard) / 3)
    return dis


# 使用TF-IDF计算两个句子的相似度
def tf_sim_cal(sentence1, sentence2):
    # 分词、去掉特殊符号、转化为小写处理
    sentence1 = cut_sentence_process(sentence1)
    sentence2 = cut_sentence_process(sentence2)
    # 转化为TF矩阵
    cv = CountVectorizer(tokenizer=lambda s: s.split())
    corpos = [sentence1, sentence2]
    vectors = cv.fit_transform(corpos).toarray()
    # 计算TF系数
    return np.dot(vectors[0], vectors[1]) / (norm(vectors[0]) * norm(vectors[1]))


# 将计算句子向量得到的相似度和TF-IDF计算得到的相似度求均值作为最终的相似度
def sim_cal(model, sentence1, sentence2):
    word2vec_sim = word2vec_sim_cal(model, sentence1, sentence2)
    tf_sim = tf_sim_cal(sentence1, sentence2)

    sim = float((word2vec_sim + tf_sim) / 2)
    return sim