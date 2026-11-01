<template>
  <div class="editor">
    <div class="toolbar">
      <div class="left">
        <el-button @click="onBack">返回</el-button>
        <span class="wf-name">{{ workflow?.name || '加载中…' }}</span>
        <el-tag v-if="dirty" type="warning" size="small">未保存</el-tag>
        <el-tag v-if="!canWrite" type="info" size="small">只读（viewer）</el-tag>
      </div>
      <div class="right">
        <el-select v-model="currentVersionId" placeholder="选择版本" style="width: 200px" @change="onVersionChange">
          <el-option v-for="v in versions" :key="v.id" :value="v.id" :label="`v${v.versionNo}（${VERSION_STATUS_TEXT[v.status]}）`" />
        </el-select>
        <el-button :disabled="!canWrite" @click="autoArrange">自动布局</el-button>
        <el-button type="danger" plain :disabled="!canWrite || !hasSelection" @click="removeSelected">删除选中</el-button>
        <el-button type="primary" :loading="saving" :disabled="!canWrite" @click="onSave">保存为新版本</el-button>
      </div>
    </div>
    <div class="body">
      <div v-if="canWrite" class="palette">
        <div class="palette-title">节点（拖入画布）</div>
        <div
          v-for="(m, t) in NODE_TYPE_META"
          :key="t"
          class="palette-item"
          :style="{ borderColor: m.color }"
          draggable="true"
          @dragstart="onDragStart($event, t as NodeType)"
        >
          <span class="dot" :style="{ background: m.color }" />{{ m.label }}
        </div>
        <div class="palette-tip">连线规则：从底部圆点拖到顶部圆点；触发器无入边；条件分支出边自动标记 true/false，双击边可切换。</div>
      </div>
      <div ref="graphRef" class="canvas" @dragover.prevent @drop="onDrop"></div>
      <div v-if="selected" class="config">
        <NodeConfigPanel
          :node-id="selected.id"
          :type="selected.type"
          :name="selected.name"
          :config="selected.config"
          :readonly="!canWrite"
          @update="onConfigUpdate"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { Graph } from '@antv/x6'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getVersion, getWorkflow, pageVersions, saveVersion } from '@/api/workflow'
import { autoLayout, dslToGraphData, genNodeId, graphToDsl, NODE_TYPE_META, nodeAttrs, portGroups, precheckDsl, validateNodeConfig, type NodeData } from '@/utils/dsl'
import { VERSION_STATUS_TEXT } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import type { Dsl, NodeType, Workflow, WorkflowVersion } from '@/types'
import type { Cell } from '@antv/x6'
import NodeConfigPanel from '@/components/node-config-panel.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const canWrite = auth.canWrite

const workflowId = Number(route.params.id)
const workflow = ref<Workflow | null>(null)
const versions = ref<WorkflowVersion[]>([])
const currentVersionId = ref<number>()
/** 当前已载入画布的版本（用于取消切换时回退） */
const loadedVersionId = ref<number>()
const graphRef = ref<HTMLDivElement>()
const saving = ref(false)
const dirty = ref(false)
const loading = ref(false)
const selected = ref<{ id: string; type: NodeType; name: string; config: Record<string, unknown> } | null>(null)
const selectedCellId = ref<string | null>(null)
const selectedIsNode = ref(true)

let graph: Graph | null = null
const hasSelection = computed(() => !!selectedCellId.value)

/** 坐标缓存：仅存 localStorage，不进 DSL（DSL 严格对齐后端 DslDocument） */
const layoutKey = () => `swa_layout_wf_${workflowId}`

onMounted(async () => {
  initGraph()
  workflow.value = await getWorkflow(workflowId)
  await loadVersions()
  const qv = Number(route.query.versionId)
  if (qv && versions.value.some((v) => v.id === qv)) {
    currentVersionId.value = qv
  }
  if (currentVersionId.value) {
    await loadVersion(currentVersionId.value)
  }
  window.addEventListener('beforeunload', onBeforeUnload)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
  window.removeEventListener('keydown', onKeydown)
  graph?.dispose()
})

/** FE-2.4：未保存离开提示（路由级 + 浏览器级） */
onBeforeRouteLeave(async () => {
  if (!dirty.value) return true
  try {
    await ElMessageBox.confirm('画布有未保存修改，离开将丢失，确认离开？', '未保存提示', { type: 'warning', confirmButtonText: '离开', cancelButtonText: '留下' })
    return true
  } catch {
    return false
  }
})

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (dirty.value) e.preventDefault()
}

function initGraph() {
  graph = new Graph({
    container: graphRef.value!,
    autoResize: true,
    grid: { visible: true, size: 10 },
    panning: true,
    mousewheel: { enabled: true, modifiers: ['ctrl'] },
    // viewer 只读：禁用全部画布交互（双保险前端半）
    interacting: canWrite,
    connecting: {
      snap: { radius: 20 },
      allowBlank: false,
      allowLoop: false,
      allowMulti: false,
      allowNode: false,
      allowEdge: false,
      validateConnection: (args) => validateConn(args)
    }
  })

  graph.on('node:click', ({ node }) => {
    selectedCellId.value = node.id
    selectedIsNode.value = true
    const data = node.getData() as NodeData
    selected.value = { id: node.id, type: data.type, name: data.name, config: { ...(data.config || {}) } }
  })
  graph.on('edge:click', ({ edge }) => {
    selectedCellId.value = edge.id
    selectedIsNode.value = false
    selected.value = null
  })
  graph.on('blank:click', () => {
    selectedCellId.value = null
    selected.value = null
  })
  // 条件分支出边自动标记 branch（第一条 true，第二条 false）
  graph.on('edge:connected', ({ edge, isNew }) => {
    if (!isNew || !graph) return
    const sourceNode = graph.getCellById(edge.getSourceCellId())
    if (sourceNode?.isNode() && (sourceNode.getData() as NodeData)?.type === 'condition') {
      const siblings = graph.getEdges().filter((e) => e.getSourceCellId() === sourceNode.id && e.id !== edge.id)
      const used = new Set(siblings.map((e) => (e.getData() as { branch?: string })?.branch))
      const branch = !used.has('true') ? 'true' : 'false'
      setEdgeBranch(edge.id, branch)
    }
    markDirty()
  })
  // 双击条件出边切换 true/false
  graph.on('edge:dblclick', ({ edge }) => {
    if (!canWrite || !graph) return
    const sourceNode = graph.getCellById(edge.getSourceCellId())
    if (sourceNode?.isNode() && (sourceNode.getData() as NodeData)?.type === 'condition') {
      const cur = (edge.getData() as { branch?: string })?.branch === 'true' ? 'false' : 'true'
      setEdgeBranch(edge.id, cur)
      markDirty()
      ElMessage.info(`分支已切换为 ${cur}`)
    }
  })
  ;(['node:added', 'node:removed', 'edge:removed', 'node:moved'] as const).forEach((evt) => graph!.on(evt, () => markDirty()))
}

/** 入出度约束提示（FE-2.1）：触发器无入边/禁重复边/禁成环，非法连线即时提示 */
function validateConn(args: {
  sourceCell?: Cell | null
  targetCell?: Cell | null
  sourceMagnet?: Element | null
  targetMagnet?: Element | null
}): boolean {
  const g = graph
  if (!g) return false
  const { sourceCell, targetCell, sourceMagnet, targetMagnet } = args
  if (!sourceMagnet || !targetMagnet) return false
  if (sourceMagnet.getAttribute('port-group') !== 'out' || targetMagnet.getAttribute('port-group') !== 'in') return false
  if (!sourceCell || !targetCell || sourceCell === targetCell) return false
  const targetType = (targetCell.getData() as NodeData)?.type
  if (targetType === 'mqtt-trigger') {
    ElMessage.warning('MQTT 触发节点不允许有入边')
    return false
  }
  const dup = g.getEdges().some((e) => e.getSourceCellId() === sourceCell.id && e.getTargetCellId() === targetCell.id)
  if (dup) {
    ElMessage.warning('两节点间已存在连线')
    return false
  }
  if (wouldCycle(sourceCell.id, targetCell.id)) {
    ElMessage.warning('该连线会形成环形依赖')
    return false
  }
  return true
}

/** 成环检测：新边 source→target 成环 ⟺ target 可达 source（DFS） */
function wouldCycle(sourceId: string, targetId: string): boolean {
  const g = graph!
  const stack = [targetId]
  const seen = new Set<string>()
  while (stack.length) {
    const cur = stack.pop()!
    if (cur === sourceId) return true
    if (seen.has(cur)) continue
    seen.add(cur)
    g.getEdges()
      .filter((e) => e.getSourceCellId() === cur)
      .forEach((e) => stack.push(e.getTargetCellId()))
  }
  return false
}

function setEdgeBranch(edgeId: string, branch: 'true' | 'false') {
  const edge = graph?.getCellById(edgeId)
  if (!edge?.isEdge()) return
  edge.setData({ branch })
  edge.setLabels([{ attrs: { label: { text: branch, fill: branch === 'true' ? '#27ae60' : '#c0392b', fontSize: 12 } } }])
}

function markDirty() {
  if (!loading.value) dirty.value = true
}

async function loadVersions() {
  const data = await pageVersions(workflowId, { pageNo: 1, pageSize: 100 })
  versions.value = data.records
  if (!currentVersionId.value && data.records.length) currentVersionId.value = data.records[0].id
}

async function loadVersion(versionId: number) {
  loading.value = true
  try {
    const v = await getVersion(versionId)
    const dsl = JSON.parse(v.dslJson) as Dsl
    const savedPos = readPositions()
    const gdata = dslToGraphData(dsl, savedPos)
    graph?.fromJSON(gdata)
    selected.value = null
    selectedCellId.value = null
    loadedVersionId.value = versionId
    dirty.value = false
  } finally {
    loading.value = false
  }
}

function readPositions(): Record<string, { x: number; y: number }> | undefined {
  try {
    const raw = localStorage.getItem(layoutKey())
    return raw ? JSON.parse(raw) : undefined
  } catch {
    return undefined
  }
}

function persistPositions() {
  const pos: Record<string, { x: number; y: number }> = {}
  graph?.getNodes().forEach((n) => {
    pos[n.id] = n.getPosition()
  })
  localStorage.setItem(layoutKey(), JSON.stringify(pos))
}

async function onVersionChange(versionId: number) {
  if (dirty.value) {
    try {
      await ElMessageBox.confirm('切换版本将丢弃未保存修改，确认切换？', '未保存提示', { type: 'warning' })
    } catch {
      currentVersionId.value = loadedVersionId.value
      return
    }
  }
  await loadVersion(versionId)
}

/** 拖入节点（FE-2.1）：HTML5 DnD，无需额外插件 */
function onDragStart(e: DragEvent, type: NodeType) {
  e.dataTransfer?.setData('text/swa-node-type', type)
}

function onDrop(e: DragEvent) {
  if (!graph || !canWrite) return
  const type = e.dataTransfer?.getData('text/swa-node-type') as NodeType
  if (!type || !NODE_TYPE_META[type]) return
  const p = graph.clientToGraph(e.clientX, e.clientY)
  const id = genNodeId(type, graph)
  graph.addNode({
    id,
    shape: 'rect',
    x: p.x - 80,
    y: p.y - 28,
    width: 160,
    height: 56,
    label: NODE_TYPE_META[type].label,
    attrs: nodeAttrs(NODE_TYPE_META[type].color),
    ports: portGroups(),
    data: { type, name: `${NODE_TYPE_META[type].label}-${id}`, config: {} } satisfies NodeData
  })
  markDirty()
}

function onConfigUpdate(payload: { name: string; config: Record<string, unknown> }) {
  if (!graph || !selected.value) return
  const node = graph.getCellById(selected.value.id)
  if (!node?.isNode()) return
  const data: NodeData = { type: selected.value.type, name: payload.name, config: payload.config }
  node.setData(data)
  node.attr('label/text', payload.name)
  selected.value = { ...selected.value, name: payload.name, config: payload.config }
  markDirty()
}

function removeSelected() {
  if (!graph || !selectedCellId.value || !canWrite) return
  const cell = graph.getCellById(selectedCellId.value)
  if (cell) graph.removeCell(cell)
  selected.value = null
  selectedCellId.value = null
  markDirty()
}

function onKeydown(e: KeyboardEvent) {
  if ((e.key === 'Delete' || e.key === 'Backspace') && canWrite) {
    const tag = (e.target as HTMLElement)?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA') return
    removeSelected()
  }
}

function autoArrange() {
  if (!graph || !canWrite) return
  const dsl = JSON.parse(graphToDsl(graph)) as Dsl
  const pos = autoLayout(dsl)
  graph.getNodes().forEach((n) => {
    if (pos[n.id]) n.setPosition(pos[n.id].x, pos[n.id].y)
  })
  markDirty()
}

/** 保存（FE-2.3）：结构预检 + 逐节点配置校验 → POST 新版本（draft） */
async function onSave() {
  if (!graph) return
  const dslJson = graphToDsl(graph)
  const dsl = JSON.parse(dslJson) as Dsl
  const structuralErr = precheckDsl(dsl)
  if (structuralErr) {
    ElMessage.error(structuralErr)
    return
  }
  for (const n of dsl.nodes) {
    const cfgErr = validateNodeConfig(n.type, n.config)
    if (cfgErr) {
      ElMessage.error(`「${n.name}」${cfgErr}`)
      return
    }
  }
  saving.value = true
  try {
    const v = await saveVersion(workflowId, dslJson)
    persistPositions()
    dirty.value = false
    ElMessage.success(`已保存为新版本 v${v.versionNo}（draft），可在版本管理中发布`)
    await loadVersions()
    currentVersionId.value = v.id
  } finally {
    saving.value = false
  }
}

async function onBack() {
  router.push('/workflows')
}
</script>

<style scoped>
.editor { display: flex; flex-direction: column; height: 100%; }
.toolbar { display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: #fff; border-bottom: 1px solid #e4e7ed; }
.left, .right { display: flex; align-items: center; gap: 10px; }
.wf-name { font-weight: 600; }
.body { flex: 1; display: flex; min-height: 0; }
.palette { width: 180px; background: #fff; border-right: 1px solid #e4e7ed; padding: 12px; overflow: auto; }
.palette-title { font-size: 12px; color: #909399; margin-bottom: 8px; }
.palette-item { display: flex; align-items: center; gap: 8px; border: 1px solid; border-radius: 6px; padding: 8px 10px; margin-bottom: 8px; cursor: grab; background: #fff; font-size: 13px; }
.palette-item:hover { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12); }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.palette-tip { font-size: 12px; color: #909399; line-height: 1.6; margin-top: 8px; }
.canvas { flex: 1; min-width: 0; }
.config { width: 340px; background: #fff; border-left: 1px solid #e4e7ed; overflow: auto; }
</style>
