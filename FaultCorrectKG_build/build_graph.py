# 生成图谱，存入neo4j数据库
from py2neo import Graph, Node, Relationship, NodeMatcher, RelationshipMatcher
import json
import csv
from similarity_calculate import sim_cal
from knowledge_verify import solution_verify


# 读取知识抽取结果csv文件，日志所属模板结果json文件，初步创建节点和关系
def build_graph(graph, knowledge_extract_result_file_path, template_result_file_path):
    template_result_file = open(template_result_file_path)
    template_result_dic = json.load(template_result_file)
    template_result_file.close()

    knowledge_extract_result_file = open(knowledge_extract_result_file_path)
    reader = list(csv.reader(knowledge_extract_result_file))
    knowledge_extract_result_file.close()

    matcher = NodeMatcher(graph)

    for row_list in reader:
        page_index = row_list[0][7:].strip()

        # 故障节点
        fault_node_name = 'fault-' + str(reader.index(row_list) + 1)
        fault_node = Node('fault', name=fault_node_name)
        graph.create(fault_node)

        # 连接故障描述节点
        description = row_list[1][13:].strip()
        description_node = Node('description',
                                name='description of '+fault_node_name,
                                content=description)
        graph.create(description_node)

        has_description = Relationship(fault_node, 'has_description', description_node)
        graph.create(has_description)

        # 连接tag节点
        tag_str = row_list[2][6:].strip()
        if len(tag_str) > 0:
            tags = tag_str.split('   ')
            for tag in tags:
                tag_node = matcher.match('tag', name=tag).first()
                if not tag_node:
                    tag_node = Node('tag', name=tag)
                    graph.create(tag_node)
                has_tag = Relationship(fault_node, 'has_tag', tag_node)
                graph.create(has_tag)

        # 如果有日志的话，连接故障日志节点，如果有多份日志，就创建多个故障日志节点
        logs = [element for element in row_list if element.find('[LOG]') == 0]
        for log_index in range(0, len(logs)):
            log = logs[log_index][5:].strip()
            log_node = Node('log',
                            name='log-'+str(log_index+1)+' of '+fault_node_name,
                            content=log)
            graph.create(log_node)

            has_log = Relationship(fault_node, 'has_log', log_node)
            graph.create(has_log)

            # 日志节点连接所属的所有日志模板节点
            log_index = str(log_index)
            if page_index in template_result_dic and log_index in template_result_dic[page_index]:
                templates = template_result_dic[page_index][log_index]
                for template in templates:
                    template_node = matcher.match('template', name=template).first()
                    if not template_node:
                        template_node = Node('template', name=template)
                        graph.create(template_node)
                    has_template = Relationship(log_node, 'has_template', template_node)
                    graph.create(has_template)

        # 连接故障原因节点和故障修复方案节点
        reason_indexs = [index for index in range(0, len(row_list)) if row_list[index].find('[REASON]') == 0]
        not_null_reason_count = 0  # 记录非空的故障原因数目
        for index in range(0, len(reason_indexs)):
            reason_index = reason_indexs[index]

            # 读取故障原因
            reason_text = json.loads(row_list[reason_index][8:].strip())['value']

            # 如果故障原因存在，故障节点连接故障原因节点，故障原因节点再连接故障修复方案节点；否则，故障节点直接连接故障修复方案节点
            solution_html = row_list[reason_index + 1][15:].strip()
            solution_json = row_list[reason_index + 2][15:].strip()
            vote = row_list[reason_index + 3][6:].strip()

            is_solution_valid = solution_verify(json.loads(solution_json), int(vote))  # 校验故障修复方案是否有效

            if reason_text:
                not_null_reason_count += 1
                # 创建故障原因节点
                reason_content = '\n'.join(reason_text)
                reason_node = Node('reason',
                                   name='reason-'+str(not_null_reason_count)+' of '+fault_node_name,
                                   content=reason_content)
                graph.create(reason_node)

                has_reason = Relationship(fault_node, 'has_reason', reason_node)
                graph.create(has_reason)

                # 如果故障修复方案有效，就创建故障修复方案节点并连接
                if is_solution_valid:
                    solution_node = Node('solution',
                                         name='solution-'+str(index+1)+' of '+fault_node_name+' for '+'reason-'+str(not_null_reason_count),
                                         html_content=solution_html, json_content=solution_json, vote=vote)
                    graph.create(solution_node)

                    has_solution = Relationship(reason_node, 'has_solution', solution_node)
                    graph.create(has_solution)
            elif is_solution_valid:
                solution_node = Node('solution',
                                     name='solution-'+str(index+1)+' of '+fault_node_name,
                                     html_content=solution_html, json_content=solution_json, vote=vote)
                graph.create(solution_node)

                has_solution = Relationship(fault_node, 'has_solution', solution_node)
                graph.create(has_solution)


# 获取一个日志节点连接的所有日志模板
def get_log_templates(graph, log_node):
    relationship_matcher = RelationshipMatcher(graph)

    templates = []

    has_templates = relationship_matcher.match(r_type='has_template', nodes=[log_node])
    for has_template in has_templates:
        print(has_template)
        templates.append(has_template.end_node.identity)

    return templates


# 统计日志之间相同日志模板的数量，并将数量超过阈值的日志节点连接起来
def link_logs(graph):
    node_matcher = NodeMatcher(graph)
    log_node_list = list(node_matcher.match('log'))

    while log_node_list:
        log_node1 = log_node_list.pop()
        templates1 = get_log_templates(graph, log_node1)
        for log_node2 in log_node_list:
            templates2 = get_log_templates(graph, log_node2)
            same_templates = len(set(templates1) & set(templates2))
            if same_templates > 0:
                has_same_templates = Relationship(log_node1, 'has_same_templates', log_node2, same_templates=same_templates)
                graph.create(has_same_templates)


# 读取日志模板文件，给日志模板增加content属性，以存储模板的实际内容
def add_template_content(graph, log_template_content_file_path):
    log_template_content_file = open(log_template_content_file_path)
    reader = list(csv.reader(log_template_content_file))[1:]
    log_template_content_file.close()

    # 根据模板的name查找到对应的节点，增加属性centent
    for row_list in reader:
        template_name = row_list[0]
        template_content = row_list[1]

        matcher = NodeMatcher(graph)
        template_node = matcher.match('template', name=template_name).first()

        if template_node:
            template_node.update({'content': template_content})
            graph.push(template_node)


# 将图谱中某类节点通过content相似度连接起来
# sim_cal_method取0代表使用word2vec计算相似度，需要提供model的路径；sim_cal_method取1代表使用tf-id计算相似度
def link_nodes_by_similarity(graph, type):
    matcher = NodeMatcher(graph)
    node_list = list(matcher.match(type))

    model_dir = './data/similarity_calculate_data/word2vec_model/'
    if type == 'description':
        model = model_dir + 'description_model'
    elif type == 'reason':
        model = model_dir + 'reason_model'

    while node_list:
        node1 = node_list.pop()
        for node2 in node_list:
            similarity = sim_cal(model, node1.get('content'), node2.get('content'))
            if similarity > 0:
                has_similarity = Relationship(node1, 'has_similarity', node2, similarity=similarity)
                graph.create(has_similarity)


if __name__ == '__main__':
    graph = Graph('http://localhost:7474', username='neo4j', password='neo4j')  # 连接neo4j数据库
    graph.delete_all()  # 删除历史数据

    # 初步创建图谱节点和关系
    build_graph(graph=graph,
                knowledge_extract_result_file_path='./data/knowledge_extract_result/knowledge_extract_result.csv',
                template_result_file_path='./data/log_data/template_result.json',)

    # 连接故障日志节点
    link_logs(graph)

    # 给所有的日志模板节点增加模板内容属性
    add_template_content(graph=graph,
                         log_template_content_file_path='./data/log_data/log_templates/log_train.log_templates.csv')

    # 连接故障描述和故障原因
    link_nodes_by_similarity(graph=graph, type='description')
    link_nodes_by_similarity(graph=graph, type='reason')