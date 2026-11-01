<template>
  <div style="padding:20px">
    <h1>SaaS自动化工作流平台</h1>
    <el-space style="margin-bottom:16px">
      <el-button @click="addNode('start')">+ 开始节点</el-button>
      <el-button @click="addNode('http')">+ HTTP节点</el-button>
      <el-button @click="addNode('agent')">+ Agent节点</el-button>
      <el-button @click="addNode('branch')">+ 条件分支</el-button>
      <el-button @click="addNode('end')">+ 结束节点</el-button>
      <el-button type="primary" @click="saveFlow">保存流程</el-button>
      <el-button type="success" @click="runFlow">执行流程</el-button>
    </el-space>
    <div ref="canvas" style="height:450px;border:1px solid #eee;background:#f5f5f5"></div>
    <el-divider />
    <el-card v-if="runResult">
      <h3>执行结果</h3>
      <p>状态：{{ runResult.status }}</p>
      <p>当前节点：{{ runResult.currentNode }}</p>
      <p>结果：{{ runResult.result }}</p>
    </el-card>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { Graph } from '@antv/x6'
import axios from 'axios'
import { ElMessage } from 'element-plus'
const canvas = ref(null)
const runResult = ref(null)
let graph = null
let n = 0
let savedFlowId = null

onMounted(() => { graph = new Graph({ container: canvas.value, grid: true }) })

function addNode(type) {
  const colors = { start: '#67c23a', http: '#409eff', agent: '#e6a23c', branch: '#f56c6c', end: '#909399' }
  graph.addNode({
    id: 'n' + (++n), shape: 'rect',
    x: 50 + (n-1)*160, y: 100, width: 130, height: 50,
    attrs: { body: { fill: colors[type], rx: 6 }, label: { text: type.toUpperCase(), fill: '#fff' } }
  })
}

async function saveFlow() {
  const res = await axios.post('/api/workflows', { name: '测试流程', definitionJson: JSON.stringify(graph.toJSON()), status: 1 })
  savedFlowId = res.data.data.id
  ElMessage.success('已保存，ID=' + savedFlowId)
}

async function runFlow() {
  if (!savedFlowId) { ElMessage.warning('请先保存流程'); return }
  const res = await axios.post(`/api/workflows/${savedFlowId}/run`)
  runResult.value = res.data.data
  ElMessage.success('执行完成')
}
</script>
