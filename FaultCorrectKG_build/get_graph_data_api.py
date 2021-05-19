# 图谱可视化后端接口
import flask
from py2neo import Graph, NodeMatcher, RelationshipMatcher

server = flask.Flask(__name__)


# 将图数据库中的节点封装成json
def parse_node_to_json(node, type, properties=[]):
    json_node = {}
    json_node['id'] = str(node.identity)
    json_node['type'] = type
    json_node['name'] = node.get('name')
    for property in properties:
        json_node[property] = node.get(property)
    return json_node


# 将图数据库中的关系封装成json
def parse_relationship_to_json(relationship, type, properties=[]):
    json_relationship = {}
    json_relationship['type'] = type
    json_relationship['from'] = str(relationship.start_node.identity)
    json_relationship['to'] = str(relationship.end_node.identity)
    for property in properties:
        json_relationship[property] = relationship.get(property)
    return json_relationship


# 判断一个节点的内容是否包含特定的关键词
def judge_node_content_contains_keyword(node, keyword):
    if not keyword:
        return True
    keyword = keyword.strip()
    if len(keyword) == 0:
        return True
    node_content = node.get('content')
    if node_content.find(keyword) != -1:
        return True
    return False


# 将节点列表中有关系的节点连接起来，并将其关系封装成json
def get_relationships_from_node_list(node_list, type, properties):
    relationship_matcher = RelationshipMatcher(graph)

    json_relationships = []

    for node1 in node_list:
        for node2 in node_list:
            relationship = relationship_matcher.match(r_type=type, nodes=[node1, node2]).first()
            print(relationship)
            if relationship != None:
                json_relationships.append(parse_relationship_to_json(relationship, type, properties))
    return json_relationships


# 获取故障描述、故障日志包含特定关键词且符合特定故障标签的故障编号节点
@server.route('/get_nodes_and_relations',  methods=['get', 'post'])
def get_fault_nodes_by_keywords_and_tags():
    des_keyword = flask.request.values.get('des_keyword')
    log_fragment = flask.request.values.get('log_fragment')
    tags = flask.request.values.get('tags')
    fault_number = flask.request.values.get('fault_number')

    try:
        fault_number = int(fault_number)
    except TypeError:
        fault_number = 5

    json_nodes = []
    json_relationships = []

    # 用来连接有关系的故障描述节点
    des_node_list = []
    # 用来连接有关系的故障日志节点
    log_node_list = []
    # 用来连接有关系的故障原因节点
    reason_node_list = []

    node_matcher = NodeMatcher(graph)
    relationship_matcher = RelationshipMatcher(graph)

    fault_nodes = node_matcher.match('fault')

    fault_count = 0  # 统计查询符合条件的结果个数

    for fault_node in fault_nodes:
        # 故障描述是否含有关键词
        has_dess = relationship_matcher.match(r_type='has_description', nodes=[fault_node])
        for has_des in has_dess:
            print(has_des)
            des_node = has_des.end_node
            if judge_node_content_contains_keyword(des_node, des_keyword):
                result_has_des = has_des

        # 故障日志是否含有关键词
        result_has_logs = []
        has_logs = relationship_matcher.match(r_type='has_log', nodes=[fault_node])
        for has_log in has_logs:
            print(has_log)
            log_node = has_log.end_node
            if judge_node_content_contains_keyword(log_node, log_fragment):
                result_has_logs.append(has_log)

        # 是否含有特定故障标签
        result_has_tags = []
        has_tags = relationship_matcher.match(r_type='has_tag', nodes=[fault_node])
        for has_tag in has_tags:
            print(has_tag)
            tag_node = has_tag.end_node
            if not tags or len(tags) == 0 or tag_node.get('name') in tags[:-1].split(','):
                result_has_tags.append(has_tag)

        # 如果该故障编号节点是否符合条件
        if result_has_des != None and result_has_logs and result_has_tags:
            fault_count += 1

            # 加入故障编号节点
            json_nodes.append(parse_node_to_json(fault_node, 'fault'))

            # 加入故障描述节点
            des_node = result_has_des.end_node
            json_nodes.append(parse_node_to_json(des_node, 'description', ['content']))
            json_relationships.append(parse_relationship_to_json(result_has_des, 'has_description'))
            des_node_list.append(des_node)

            # 加入故障日志节点
            for has_log in result_has_logs:
                log_node = has_log.end_node
                json_nodes.append(parse_node_to_json(log_node, 'log', ['content']))
                json_relationships.append(parse_relationship_to_json(has_log, 'has_log'))
                log_node_list.append(log_node)

            # 加入故障标签节点
            for has_tag in result_has_tags:
                tag_node = has_tag.end_node
                json_nodes.append(parse_node_to_json(tag_node, 'tag'))
                json_relationships.append(parse_relationship_to_json(has_tag, 'has_tag'))

            # 加入故障编号节点连接的故障原因节点和该故障原因节点连接的故障修复方案节点
            has_reasons = relationship_matcher.match(r_type='has_reason', nodes=[fault_node])
            for has_reason in has_reasons:
                print(has_reason)
                reason_node = has_reason.end_node
                json_nodes.append(parse_node_to_json(reason_node, 'reason', ['content']))
                json_relationships.append(parse_relationship_to_json(has_reason, 'has_reason'))
                reason_node_list.append(reason_node)

                has_solutions = relationship_matcher.match(r_type='has_solution', nodes=[reason_node])
                for has_solution in has_solutions:
                    print(has_solution)
                    solution_node = has_solution.end_node
                    json_nodes.append(parse_node_to_json(solution_node, 'solution', ['html_content', 'vote']))
                    json_relationships.append(parse_relationship_to_json(has_solution, 'has_solution'))

            # 加入故障编号节点直接连接的故障修复方案节点
            has_solutions = relationship_matcher.match(r_type='has_solution', nodes=[fault_node])
            for has_solution in has_solutions:
                print(has_solution)
                solution_node = has_solution.end_node
                json_nodes.append(parse_node_to_json(solution_node, 'solution', ['html_content', 'vote']))
                json_relationships.append(parse_relationship_to_json(has_solution, 'has_solution'))

        if fault_count == int(fault_number):
            break

    # 连接有关系的故障描述节点
    json_relationships += get_relationships_from_node_list(des_node_list, 'has_similarity', ['similarity'])
    # 连接有关系的故障日志节点
    json_relationships += get_relationships_from_node_list(log_node_list, 'has_same_templates', ['same_templates'])
    # 连接有关系的故障原因节点
    json_relationships += get_relationships_from_node_list(reason_node_list, 'has_similarity', ['similarity'])

    result = {
        'nodes': json_nodes,
        'relationships': json_relationships,
    }

    return result


# 获取所有的故障标签
@server.route('/get_tags',  methods=['get', 'post'])
def get_tags():
    tags = []
    node_matcher = NodeMatcher(graph)
    tag_nodes = node_matcher.match('tag')
    for tag_node in tag_nodes:
        tags.append(tag_node.get('name'))

    return {
        'tags': tags,
    }


if __name__ == '__main__':
    graph = Graph('http://localhost:7474', username='neo4j', password='neo4j')  # 连接neo4j数据库

    server.run(port=5001, debug=True, host='0.0.0.0')
