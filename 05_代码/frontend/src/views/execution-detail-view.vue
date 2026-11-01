<template>
  <div>
    <el-card class="page-card">
      <div class="table-toolbar">
        <div class="title-box">
          <el-button @click="router.push('/executions')">返回</el-button>
          <span class="title">执行实例 #{{ execId }}</span>

          <el-tag v-if="detail" :type="statusTagType(detail.status)">{{ EXEC_STATUS_TEXT[detail.status] || detail.status }}</el-tag>
          <el-tag v-if="sseState === 'connected'" type="success" size="small">实时已连接</el-tag>
          <el-tag v-else-if="sseState === 'reconnecting'" type="warning" size="small">断线重连中…</el-tag>
          <el-tag v-else size="small" type="info">实时未连接</el-tag>
        </div>
        <el-button v-if="canWrite" type="primary" plain :loading="replaying" @click="onReplay">回放（按原参数重新触发）</el-button>
      </div>
      <el-descriptions v-if="detail" :column="3" border size="small">
        <el-descriptions-item label="版本ID">{{ detail.versionId }}</el-descriptions-item>
        <el-descriptions-item label="触发方式">{{ detail.triggerType }}</el-descriptions-item>
        <el-descriptions-item label="失败原因">{{ detail.failReason ? FAIL_REASON_TEXT[detail.failReason] || detail.failReason : '-' }}</el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ fmtTime(detail.startedAt) }}</el-descriptions-item>
        <el-descriptions-item label="结束时间">{{ fmtTime(detail.endedAt) }}</el-descriptions-item>
        <el-descriptions-item label="触发入参"><span class="mono">{{ detail.triggerPayload || '-' }}</span></el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card class="page-card">
      <div class="table-toolbar"><span class="title">节点执行（SSE 实时刷新）</span></div>
      <el-table :data="nodes" empty-text="暂无节点执行记录">
        <el-table-column prop="nodeId" label="节点ID" width="90" />
        <el-table-column prop="nodeType" label="类型" width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ EXEC_STATUS_TEXT[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="开始时间" width="165">
          <template #default="{ row }">{{ fmtTime(row.startedAt) }}</template>
        </el-table-column>
        <el-table-column label="结束时间" width="165">
          <template #default="{ row }">{{ fmtTime(row.endedAt) }}</template>
        </el-table-column>
        <el-table-column label="错误信息" min-width="160">
          <template #default="{ row }">{{ row.errorMessage || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewNode(row)">输入/输出</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 节点输入/输出/重试日志：一律文本转义展示（禁 v-html，防 XSS） -->
    <el-drawer v-model="nodeDrawer" :title="`节点 ${currentNode?.nodeId} · 输入/输出`" size="520px">
      <template v-if="currentNode">
        <h4>输入</h4>
        <pre class="mono json">{{ prettyJson(currentNode.inputJson) }}</pre>
        <h4>输出</h4>
        <pre class="mono json">{{ prettyJson(currentNode.outputJson) }}</pre>
        <h4>重试日志</h4>
        <pre class="mono json">{{ prettyJson(currentNode.retryLog) }}</pre>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getExecution, getExecutionNodes, replayExecution } from '@/api/execution'
import { ExecutionEventStream } from '@/utils/sse'
import { EXEC_STATUS_TEXT, FAIL_REASON_TEXT, fmtTime, prettyJson, statusTagType } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import type { Execution, NodeExecution } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const canWrite = auth.canWrite

const execId = ref(Number(route.params.id))
const detail = ref<Execution | null>(null)
const nodes = ref<NodeExecution[]>([])
const sseState = ref<'idle' | 'connected' | 'reconnecting'>('idle')
const replaying = ref(false)
const nodeDrawer = ref(false)
const currentNode = ref<NodeExecution | null>(null)

let stream: ExecutionEventStream | null = null

onMounted(() => void init())

onBeforeUnmount(() => stream?.close())

// 回放跳转到新实例（同路由不同参数，组件复用需手动重载）
watch(
  () => route.params.id,
  (v) => {
    const id = Number(v)
    if (id && id !== execId.value) {
      execId.value = id
      void init()
    }
  }
)

async function init() {
  stream?.close()
  detail.value = null
  nodes.value = []
  // 先拉详情 + 快照，再订阅 SSE（FE-4.2/FE-4.3）
  detail.value = await getExecution(execId.value)
  nodes.value = await getExecutionNodes(execId.value)
  subscribe()
}

function subscribe() {
  stream?.close()
  stream = new ExecutionEventStream(execId.value, {
    onConnected: () => (sseState.value = 'connected'),
    onReconnecting: () => (sseState.value = 'reconnecting'),
    onNode: (n) => upsertNode(n),
    onExecution: (e) => {
      if (detail.value) detail.value = { ...detail.value, ...e }
      // 终态后主动断开，不再重连
      if (e.status === 'SUCCESS' || e.status === 'FAILED') {
        stream?.close()
        sseState.value = 'idle'
      }
    }
  })
  stream.start()
}

function upsertNode(n: NodeExecution) {
  const idx = nodes.value.findIndex((x) => x.nodeId === n.nodeId)
  if (idx >= 0) nodes.value[idx] = { ...nodes.value[idx], ...n }
  else nodes.value.push(n)
}

function viewNode(row: NodeExecution) {
  currentNode.value = row
  nodeDrawer.value = true
}

/** FE-4.4 回放：复制触发入参新建执行，跳转到新实例 */
async function onReplay() {
  replaying.value = true
  try {
    const exec = await replayExecution(execId.value)
    ElMessage.success(`已回放，新实例 #${exec.id}`)
    router.push(`/executions/${exec.id}`)
  } finally {
    replaying.value = false
  }
}
</script>

<style scoped>
.title-box { display: flex; align-items: center; gap: 10px; }
.title { font-weight: 600; }
.json { background: #f5f7fa; border-radius: 4px; padding: 10px; max-height: 220px; overflow: auto; }
</style>
