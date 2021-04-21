<template>
  <div class="faultCorrectGraphPage">
    <el-form :inline="true" :model="kg_search_data" class="form-search">
      <el-form-item label="故障描述" size="medium">
        <el-input
          v-model="kg_search_data.des_keyword"
          placeholder="关键词"
        ></el-input>
      </el-form-item>
      <el-form-item label="故障标签" size="medium" class="tags-input">
        <el-select
          v-model="kg_search_data.selected_tags"
          multiple
          filterable
          placeholder="可多选"
        >
          <el-option v-for="tag in tags" :key="tag" :label="tag" :value="tag">
          </el-option>
        </el-select>
      </el-form-item>
      <el-form-item label="故障日志" size="medium" class="log-input">
        <el-input
          v-model="kg_search_data.log_fragment"
          placeholder="关键片段"
        ></el-input>
      </el-form-item>
      <el-form-item size="medium">
        <el-button type="primary" @click="onSubmit">查询</el-button>
      </el-form-item>
      <el-form-item label="节点筛选" size="mini">
        <el-radio-group v-model="selected_node_type" @change="doFilter">
          <el-radio-button label="全部"></el-radio-button>
          <el-radio-button label="故障编号"></el-radio-button>
          <el-radio-button label="故障描述"></el-radio-button>
          <el-radio-button label="故障标签"></el-radio-button>
          <el-radio-button label="故障日志"></el-radio-button>
          <el-radio-button label="故障原因"></el-radio-button>
          <el-radio-button label="故障修复方案"></el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="显示故障个数" size="mini" class="node-number-select">
        <el-radio-group v-model="selected_fault_number" @change="doFilter">
          <el-radio :label="1"></el-radio>
          <el-radio :label="2"></el-radio>
          <el-radio :label="3"></el-radio>
          <el-radio :label="5"></el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="关系筛选" size="mini">
        <el-checkbox-group v-model="checklist_relation_type" @change="doFilter">
          <el-checkbox label="has_description"></el-checkbox>
          <el-checkbox label="has_tag"></el-checkbox>
          <el-checkbox label="has_log"></el-checkbox>
          <el-checkbox label="has_reason"></el-checkbox>
          <el-checkbox label="has_solution"></el-checkbox>
          <el-checkbox label="has_same_templates"></el-checkbox>
          <el-checkbox label="has_similarity"></el-checkbox>
        </el-checkbox-group>
      </el-form-item>
    </el-form>
    <div class="node-explain">
      <p><i class="icon fault el-icon-warning" /> 故障编号</p>
      <p><i class="icon des el-icon-tickets" /> 故障描述</p>
      <p><i class="icon tag el-icon-s-flag" /> 故障标签</p>
      <p><i class="icon log el-icon-info" /> 故障日志</p>
      <p><i class="icon reason el-icon-question" /> 故障原因</p>
      <p><i class="icon solution el-icon-s-opportunity" /> 故障修复方案</p>
    </div>
    <div ref="faultCorrectKg" class="kg-content">
      <SeeksRelationGraph ref="seeksRelationGraph" :options="graphOptions">
        <div slot="node" slot-scope="{ node }">
          <el-popover placement="right" trigger="click">
            <div class="node-panel">
              <p>类型：{{ node.data.type }}</p>
              <hr />
              <p>名称：{{ node.data.name }}</p>
              <div v-if="node.data.type == '故障修复方案'">
                <hr />
                <p>得票数：{{ node.data.vote }}</p>
              </div>
              <div
                v-if="
                  (node.data.type != '故障编号') &
                  (node.data.type != '故障标签')
                "
                class="node-content"
              >
                <hr />
                <p>内容：</p>
                <el-scrollbar>
                  <div
                    class="log-or-solution"
                    v-html="'<pre><code>' + node.data.content + '</code></pre>'"
                    v-if="node.data.type == '故障日志'"
                  ></div>
                  <div
                    class="log-or-solution"
                    v-html="node.data.html_content"
                    v-else-if="node.data.type == '故障修复方案'"
                  ></div>
                  <p v-else>{{ node.data.content }}</p>
                </el-scrollbar>
              </div>
            </div>
            <div slot="reference" style="cursor: pointer">
              <i class="node-icon" :class="node.data.icon" />
            </div>
          </el-popover>
        </div>
      </SeeksRelationGraph>
    </div>
  </div>
</template>

<script>
import SeeksRelationGraph from "relation-graph";
import axios from "axios";

export default {
  name: "faultCorrectKG",
  components: { SeeksRelationGraph },
  data() {
    return {
      graph_json_data: {
        nodes: [],
        links: [],
      },
      kg_search_data: {
        des_keyword: "",
        selected_tags: [],
        log_fragment: "",
      },
      tags: [],
      selected_fault_number: 5,
      selected_node_type: "全部",
      checklist_relation_type: [
        "has_description",
        "has_tag",
        "has_log",
        "has_reason",
        "has_solution",
        "has_same_templates",
        "has_similarity",
      ],
      graphOptions: {
        allowSwitchLineShape: true,
        allowSwitchJunctionPoint: true,
        defaultJunctionPoint: "border",
        defaultNodeFontColor: "white",
        defaultNodeWidth: 30,
        defaultNodeHeight: 30,
        defaultLineShape: 1,
        defaultLineColor: "#666666",
        layouts: [
          {
            label: "自动布局",
            layoutName: "force",
            layoutClassName: "seeks-layout-force",
          },
        ],
      },
    };
  },
  mounted() {
    this.getTags();
    this.setGraphData();
  },
  methods: {
    onSubmit() {
      this.selected_fault_number = 5;
      this.selected_node_type = "全部";
      this.checklist_relation_type = [
        "has_description",
        "has_tag",
        "has_log",
        "has_reason",
        "has_solution",
        "has_same_templates",
        "has_similarity",
      ];

      var des_keyword = this.kg_search_data.des_keyword;
      var selected_tags = "";
      this.kg_search_data.selected_tags.forEach((tag) => {
        selected_tags = selected_tags + tag + ",";
      });
      var log_fragment = this.kg_search_data.log_fragment;
      this.setGraphData(des_keyword, selected_tags, log_fragment);
    },
    getTags() {
      var request_url = "http://127.0.0.1:5001/get_tags";
      axios
        .get(request_url)
        .then((response) => (this.tags = response.data.tags))
        .catch((error) => console.log(error))
        .finally(() => console.log(""));
    },
    setGraphData(des_keyword, selected_tags, log_fragment) {
      const loading = this.$loading({
        lock: true,
        text: "图谱数据加载中",
        background: "rgba(0, 0, 0, 0.7)",
      });

      var request_url = "http://127.0.0.1:5001/get_nodes_and_relations";
      axios
        .get(request_url, {
          params: {
            des_keyword: des_keyword,
            log_fragment: log_fragment,
            tags: selected_tags,
            fault_number: 5,
          },
        })
        .then((response) => {
          loading.close();

          var nodes = [];
          for (let item of response.data.nodes) {
            var node = {};
            node.id = item.id;
            node.data = item;
            if (item.type == "fault") {
              node.color = "#CC0033";
              node.borderColor = "#FF0033";
              node.data.type = "故障编号";
              node.data.icon = "el-icon-warning";
            }
            if (item.type == "description") {
              node.color = "#3300FF";
              node.borderColor = "#0066CC";
              node.data.type = "故障描述";
              node.data.icon = "el-icon-tickets";
            }
            if (item.type == "log") {
              node.color = "#996633";
              node.borderColor = "#CC9933";
              node.data.type = "故障日志";
              node.data.icon = "el-icon-info";
            }
            if (item.type == "tag") {
              node.color = "#CC3300";
              node.borderColor = "#FF6633";
              node.data.type = "故障标签";
              node.data.icon = "el-icon-s-flag";
            }
            if (item.type == "reason") {
              node.color = "#9900CC";
              node.borderColor = "#CC66FF";
              node.data.type = "故障原因";
              node.data.icon = "el-icon-question";
            }
            if (item.type == "solution") {
              node.color = "#00CC33";
              node.borderColor = "#66FF66";
              node.data.type = "故障修复方案";
              node.data.icon = "el-icon-s-opportunity";
            }
            nodes.push(node);
          }

          var links = [];
          for (let item of response.data.relationships) {
            var link = {};
            link.from = item.from;
            link.to = item.to;
            link.data = {};
            link.data.type = item.type;
            link.data.from = item.from;
            link.data.to = item.to;
            if (item.type == "has_similarity") {
              link.text =
                "similarity:" + parseFloat(item.similarity).toFixed(2);
              link.isHideArrow = true;
            } else if (item.type == "has_same_templates") {
              link.text = "same_templates:" + item.same_templates;
              link.isHideArrow = true;
            } else {
              link.text = item.type;
            }
            link.fontColor = "#333333";
            links.push(link);
          }

          this.graph_json_data.nodes = nodes;
          this.graph_json_data.links = links;

          this.$refs.seeksRelationGraph.setJsonData(
            this.graph_json_data,
            (seeksRGGraph) => {
              console.log(this.graph_json_data);
              console.log(seeksRGGraph);
            }
          );
        })
        .catch((error) => console.log(error))
        .finally(() => console.log(""));
    },
    doFilter() {
      var des_nodes = [];
      var log_nodes = [];
      var reason_nodes = [];
      var selected_fault_number = parseInt(this.selected_fault_number);

      /**节点筛选 */
      var all_nodes = this.$refs.seeksRelationGraph.getNodes();
      var selected_node_type = this.selected_node_type;
      all_nodes.forEach((thisNode) => {
        var node_type = thisNode.data["type"];
        if (node_type == "故障编号") {
          selected_fault_number -= 1;
        }

        if (selected_fault_number >= 0) {
          if (node_type == "故障描述") {
            des_nodes.push(thisNode.id);
          }
          if (node_type == "故障日志") {
            log_nodes.push(thisNode.id);
          }
          if (node_type == "故障原因") {
            reason_nodes.push(thisNode.id);
          }

          var _isHideThisNode = false;
          if (selected_node_type != "全部") {
            if (node_type != selected_node_type) {
              _isHideThisNode = true;
            }
          }
          thisNode.opacity = _isHideThisNode ? 0.1 : 1;
        } else {
          thisNode.opacity = 0;
        }
      });

      selected_fault_number = parseInt(this.selected_fault_number);

      /**关系筛选 */
      var all_lines = this.$refs.seeksRelationGraph.getLines();
      all_lines.forEach((thisLine) => {
        thisLine.relations.forEach((thisLink) => {
          var link_type = thisLink.data["type"];

          if (link_type == "has_description") {
            selected_fault_number -= 1;
          }

          if (selected_fault_number >= 0) {
            if (this.checklist_relation_type.indexOf(link_type) == -1) {
              thisLink.isHide = true;
            } else {
              thisLink.isHide = false;
            }
          } else {
            var link_from = thisLink.data["from"];
            var link_to = thisLink.data["to"];
            if (
              link_type == "has_same_templates" &&
              log_nodes.indexOf(link_from) != -1 &&
              log_nodes.indexOf(link_to) != -1 &&
              this.checklist_relation_type.indexOf(link_type) != -1
            ) {
              thisLink.isHide = false;
            } else if (
              link_type == "has_similarity" &&
              des_nodes.indexOf(link_from) != -1 &&
              des_nodes.indexOf(link_to) != -1 &&
              this.checklist_relation_type.indexOf(link_type) != -1
            ) {
              thisLink.isHide = false;
            } else if (
              link_type == "has_similarity" &&
              reason_nodes.indexOf(link_from) != -1 &&
              reason_nodes.indexOf(link_to) != -1 &&
              this.checklist_relation_type.indexOf(link_type) != -1
            ) {
              thisLink.isHide = false;
            } else {
              thisLink.isHide = true;
            }
          }
        });
      });
    },
  },
};
</script>
<style>
.faultCorrectGraphPage {
  padding-left: 30px;
}
hr {
  height: 1px;
  border: none;
  border-top: 1px dashed #999999;
}
.form-search {
  border-bottom: #efefef solid 1px;
}
.tags-input .el-select {
  width: 300px;
}
.log-input .el-input {
  width: 300px;
}
.node-number-select {
  margin-left: 30px;
}
.node-explain {
  position: absolute;
  z-index: 10;
  padding-top: 15px;
  background: white;
}
.node-explain p {
  color: #606266;
  font-size: 14px;
}
.node-explain .icon {
  border-radius: 50%;
  color: white;
  font-size: 15px;
  padding: 5px;
}
.fault {
  border: 3px solid #ff0033;
  background: #cc0033;
}
.des {
  border: 3px solid #0066cc;
  background: #3300ff;
}
.tag {
  border: 3px solid #ff6633;
  background: #cc3300;
}
.log {
  border: 3px solid #cc9933;
  background: #996633;
}
.reason {
  border: 3px solid #cc66ff;
  background: #9900cc;
}
.solution {
  border: 3px solid #66ff66;
  background: #00cc33;
}
.kg-content {
  width: calc(100% - 10px);
  height: calc(100vh - 10px);
}
.kg-content .node-icon {
  font-size: 30px;
}
.node-panel {
  max-width: 500px;
}
p {
  white-space: pre-line;
  word-break: keep-all;
}
.log-or-solution {
  max-height: 300px;
}
.node-content pre {
  background: #efefef;
  overflow: auto;
}
.node-content code {
  background: #efefef;
  line-height: 28px;
  font-size: 16px;
}
</style>