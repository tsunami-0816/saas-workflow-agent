<template>
  <div class="panel">
    <div class="panel-header">
      <el-tag :color="meta.color" effect="dark" size="small">{{ meta.label }}</el-tag>
      <span class="node-id">{{ nodeId }}</span>
    </div>
    <div class="panel-desc">{{ meta.desc }}</div>
    <el-form label-position="top" size="default" :disabled="readonly">
      <el-form-item label="节点名称" required :error="errors.name">
        <el-input v-model="form.name" maxlength="32" show-word-limit @input="emitUpdate" />
      </el-form-item>

      <template v-if="type === 'http'">
        <el-form-item label="请求 URL（必填，http/https）" required :error="errors.url">
          <el-input v-model="cfg.url" maxlength="512" placeholder="https://api.example.com/path" @input="emitUpdate" />
        </el-form-item>
        <el-form-item label="Method">
          <el-select v-model="cfg.method" @change="emitUpdate">
            <el-option v-for="m in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']" :key="m" :value="m" :label="m" />
          </el-select>
        </el-form-item>
        <el-form-item label="Headers（JSON 对象，可选）" :error="errors.headers">
          <el-input v-model="cfg.headersText" type="textarea" :rows="2" maxlength="1000" placeholder='{"Content-Type":"application/json"}' @input="emitUpdate" />
        </el-form-item>
        <el-form-item label="bodyTemplate（支持 ${payload.xxx} 模板，可选）">
          <el-input v-model="cfg.bodyTemplate" type="textarea" :rows="3" maxlength="2000" @input="emitUpdate" />
        </el-form-item>
        <el-form-item label="timeoutMs（100~120000）" :error="errors.timeoutMs">
          <el-input-number v-model="cfg.timeoutMs" :min="100" :max="120000" :step="1000" @change="emitUpdate" />
        </el-form-item>
        <el-form-item label="credentialId（引用凭据，可选）">
          <el-input-number v-model="cfg.credentialId" :min="1" controls-position="right" @change="emitUpdate" />
        </el-form-item>
      </template>

      <template v-else-if="type === 'condition'">
        <el-form-item label="Aviator 表达式（必填，输出布尔，出边标 true/false）" required :error="errors.expression">
          <el-input v-model="cfg.expression" type="textarea" :rows="3" maxlength="512" show-word-limit placeholder="payload.temp > 80" @input="emitUpdate" />
        </el-form-item>
      </template>

      <template v-else-if="type === 'code'">
        <el-form-item label="Aviator 沙箱表达式（必填）" required :error="errors.expression">
          <el-input v-model="cfg.expression" type="textarea" :rows="3" maxlength="512" show-word-limit placeholder="'normal: ' + payload.temp" @input="emitUpdate" />
        </el-form-item>
      </template>

      <template v-else-if="type === 'delay'">
        <el-form-item label="延时时长 delayMs（毫秒，(0, 86400000]）" required :error="errors.delayMs">
          <el-input-number v-model="cfg.delayMs" :min="1" :max="86400000" :step="1000" @change="emitUpdate" />
        </el-form-item>
      </template>

      <template v-else-if="type === 'agent'">
        <el-form-item label="任务描述 task（必填）" required :error="errors.task">
          <el-input v-model="cfg.task" type="textarea" :rows="4" maxlength="1000" show-word-limit placeholder="描述 Agent 要完成的任务" @input="emitUpdate" />
        </el-form-item>
        <el-form-item label="taskType（模型路由类型，可选）">
          <el-input v-model="cfg.taskType" maxlength="64" placeholder="默认 agent_reasoning" @input="emitUpdate" />
        </el-form-item>
      </template>

      <template v-else-if="type === 'mqtt-trigger'">
        <el-alert type="info" :closable="false" title="触发节点无需配置；topic 在「MQTT 订阅」页绑定本流程的 published 版本。" />
      </template>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { NODE_TYPE_META } from '@/utils/dsl'
import type { NodeType } from '@/types'

/** 节点配置面板（FE-2.2）：按类型渲染表单，必填/长度/格式即时校验 */
const props = defineProps<{
  nodeId: string
  type: NodeType
  name: string
  config: Record<string, unknown>
  readonly: boolean
}>()

const emit = defineEmits<{ (e: 'update', payload: { name: string; config: Record<string, unknown> }): void }>()

const meta = computed(() => NODE_TYPE_META[props.type])

const form = reactive({ name: props.name })
/** headers 在表单中以文本编辑，emit 时解析为对象 */
const cfg = reactive({
  url: '',
  method: 'GET',
  headersText: '',
  bodyTemplate: '',
  timeoutMs: 10000 as number | undefined,
  credentialId: undefined as number | undefined,
  expression: '',
  delayMs: 1000 as number | undefined,
  task: '',
  taskType: ''
})
const errors = reactive<Record<string, string>>({})

watch(
  () => props.nodeId,
  () => syncFromProps(),
  { immediate: true }
)

function syncFromProps() {
  form.name = props.name
  const c = props.config || {}
  cfg.url = String(c.url ?? '')
  cfg.method = String(c.method ?? 'GET')
  cfg.headersText = c.headers ? JSON.stringify(c.headers) : ''
  cfg.bodyTemplate = String(c.bodyTemplate ?? '')
  cfg.timeoutMs = typeof c.timeoutMs === 'number' ? c.timeoutMs : 10000
  cfg.credentialId = typeof c.credentialId === 'number' ? c.credentialId : undefined
  cfg.expression = String(c.expression ?? '')
  cfg.delayMs = typeof c.delayMs === 'number' ? c.delayMs : 1000
  cfg.task = String(c.task ?? '')
  cfg.taskType = String(c.taskType ?? '')
  Object.keys(errors).forEach((k) => delete errors[k])
}

function buildConfig(): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  if (props.type === 'http') {
    out.url = cfg.url.trim()
    out.method = cfg.method
    if (cfg.headersText.trim()) out.headers = parseHeaders(cfg.headersText.trim())
    if (cfg.bodyTemplate.trim()) out.bodyTemplate = cfg.bodyTemplate
    if (cfg.timeoutMs) out.timeoutMs = cfg.timeoutMs
    if (cfg.credentialId) out.credentialId = cfg.credentialId
  } else if (props.type === 'condition' || props.type === 'code') {
    out.expression = cfg.expression
  } else if (props.type === 'delay') {
    out.delayMs = cfg.delayMs
  } else if (props.type === 'agent') {
    out.task = cfg.task
    if (cfg.taskType.trim()) out.taskType = cfg.taskType.trim()
  }
  return out
}

function parseHeaders(text: string): Record<string, string> | string {
  try {
    const obj = JSON.parse(text)
    if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
      errors.headers = ''
      return obj as Record<string, string>
    }
  } catch {
    /* fallthrough */
  }
  errors.headers = 'Headers 须为 JSON 对象'
  return text
}

function emitUpdate() {
  // 即时校验：名称必填；URL 格式；表达式必填（长度上限由 maxlength 保证）
  errors.name = form.name.trim() ? '' : '名称必填'
  if (props.type === 'http') {
    errors.url = !cfg.url.trim()
      ? 'URL 必填'
      : /^https?:\/\/.+/.test(cfg.url.trim())
        ? ''
        : 'URL 须以 http:// 或 https:// 开头'
  }
  if (props.type === 'condition' || props.type === 'code') {
    errors.expression = cfg.expression.trim() ? '' : '表达式必填'
  }
  if (props.type === 'agent') {
    errors.task = cfg.task.trim() ? '' : '任务描述必填'
  }
  if (props.type === 'delay') {
    errors.delayMs = cfg.delayMs && cfg.delayMs > 0 && cfg.delayMs <= 86400000 ? '' : 'delayMs 须在 (0, 86400000]'
  }
  emit('update', { name: form.name, config: buildConfig() })
}
</script>

<style scoped>
.panel { padding: 12px; }
.panel-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.node-id { color: #909399; font-size: 12px; }
.panel-desc { color: #909399; font-size: 12px; margin-bottom: 12px; }
</style>
