<template>
  <el-drawer v-model="visible" :title="`版本管理 · ${workflowName}`" size="640px">
    <el-table v-loading="loading" :data="versions" empty-text="暂无版本，请在画布中保存">
      <el-table-column prop="versionNo" label="版本" width="70">
        <template #default="{ row }">v{{ row.versionNo }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)">{{ VERSION_STATUS_TEXT[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.createdAt) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="300">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEditor(row)">画布</el-button>
          <el-button v-if="canWrite && row.status === 'draft'" link type="success" @click="onPublish(row)">发布</el-button>
          <el-button v-if="canWrite && row.status === 'published'" link type="warning" @click="onDisable(row)">禁用</el-button>
          <el-button v-if="canWrite && row.status === 'published'" link type="primary" @click="openExecute(row)">执行</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 手动触发执行 -->
    <el-dialog v-model="execVisible" title="触发执行" width="520px" append-to-body :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="clientReqId（幂等键，同键重复提交只建 1 个实例）">
          <el-input v-model="execForm.clientReqId" maxlength="128" />
        </el-form-item>
        <el-form-item label="触发入参 triggerPayload（JSON，可选）">
          <el-input v-model="execForm.triggerPayload" type="textarea" :rows="4" maxlength="4000" placeholder='{"temp": 95}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="execVisible = false">取消</el-button>
        <el-button type="primary" :loading="execLoading" @click="onExecute">触发</el-button>
      </template>
    </el-dialog>
  </el-drawer>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { disableVersion, pageVersions, publishVersion } from '@/api/workflow'
import { createExecution } from '@/api/execution'
import { fmtTime, statusTagType, VERSION_STATUS_TEXT } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import type { WorkflowVersion } from '@/types'

const router = useRouter()
const auth = useAuthStore()
const canWrite = auth.canWrite

const visible = ref(false)
const loading = ref(false)
const workflowId = ref(0)
const workflowName = ref('')
const versions = ref<WorkflowVersion[]>([])

const execVisible = ref(false)
const execLoading = ref(false)
const execForm = reactive({ versionId: 0, clientReqId: '', triggerPayload: '' })

async function open(wfId: number, wfName: string) {
  workflowId.value = wfId
  workflowName.value = wfName
  visible.value = true
  await load()
}

async function load() {
  loading.value = true
  try {
    const data = await pageVersions(workflowId.value, { pageNo: 1, pageSize: 100 })
    versions.value = data.records
  } finally {
    loading.value = false
  }
}

function openEditor(row: WorkflowVersion) {
  visible.value = false
  router.push({ path: `/workflows/${row.workflowId}/edit`, query: { versionId: String(row.id) } })
}

async function onPublish(row: WorkflowVersion) {
  await publishVersion(row.id)
  ElMessage.success(`v${row.versionNo} 已发布`)
  await load()
}

async function onDisable(row: WorkflowVersion) {
  await ElMessageBox.confirm(`禁用后 v${row.versionNo} 不可再执行，确认禁用？`, '禁用确认', { type: 'warning' })
  await disableVersion(row.id)
  ElMessage.success(`v${row.versionNo} 已禁用`)
  await load()
}

function openExecute(row: WorkflowVersion) {
  execForm.versionId = row.id
  execForm.clientReqId = `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  execForm.triggerPayload = ''
  execVisible.value = true
}

async function onExecute() {
  const payload = execForm.triggerPayload.trim()
  if (payload) {
    try {
      JSON.parse(payload)
    } catch {
      ElMessage.error('triggerPayload 不是合法 JSON')
      return
    }
  }
  execLoading.value = true
  try {
    const exec = await createExecution({ versionId: execForm.versionId, clientReqId: execForm.clientReqId.trim(), triggerPayload: payload || undefined })
    ElMessage.success(`执行实例 #${exec.id} 已创建`)
    execVisible.value = false
    visible.value = false
    router.push(`/executions/${exec.id}`)
  } finally {
    execLoading.value = false
  }
}

defineExpose({ open })
</script>
