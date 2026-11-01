<template>
  <el-card class="page-card">
    <div class="table-toolbar">
      <span class="title">MQTT 订阅（消息到达后按 topic 通配匹配触发流程执行）</span>
      <el-button v-if="auth.canWrite" type="primary" @click="openForm()">新增订阅</el-button>
    </div>
    <el-table v-loading="loading" :data="list" empty-text="暂无订阅">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="topic" label="Topic" min-width="220" />
      <el-table-column prop="workflowVersionId" label="绑定版本ID" width="110" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)">{{ row.status === 'active' ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.createdAt) }}</template>
      </el-table-column>
      <el-table-column v-if="auth.canWrite" label="操作" width="140">
        <template #default="{ row }">
          <el-button link type="primary" @click="openForm(row)">编辑</el-button>
          <el-button link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination background layout="total, prev, pager, next" :total="total" :page-size="query.pageSize" :current-page="query.pageNo" @current-change="onPage" />
    </div>

    <el-dialog v-model="formVisible" :title="form.id ? '编辑订阅' : '新增订阅'" width="520px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="Topic" prop="topic">
          <el-input v-model="form.topic" maxlength="255" placeholder="factory/+/temperature" />
        </el-form-item>
        <el-form-item label="绑定流程" prop="workflowId">
          <el-select v-model="form.workflowId" placeholder="选择流程" @change="onWorkflowChange">
            <el-option v-for="w in workflows" :key="w.id" :value="w.id" :label="w.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定版本" prop="workflowVersionId">
          <el-select v-model="form.workflowVersionId" placeholder="选择版本">
            <el-option v-for="v in versionOptions" :key="v.id" :value="v.id" :label="`v${v.versionNo}（${VERSION_STATUS_TEXT[v.status]}）`" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio value="active">启用</el-radio>
            <el-radio value="disabled">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { createSubscription, deleteSubscription, pageSubscriptions, updateSubscription } from '@/api/mqtt'
import { pageVersions, pageWorkflows } from '@/api/workflow'
import { fmtTime, statusTagType, VERSION_STATUS_TEXT } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import type { MqttSubscription, Workflow, WorkflowVersion } from '@/types'

const auth = useAuthStore()
const loading = ref(false)
const list = ref<MqttSubscription[]>([])
const total = ref(0)
const query = reactive({ pageNo: 1, pageSize: 20 })

const workflows = ref<Workflow[]>([])
const versionOptions = ref<WorkflowVersion[]>([])

const formVisible = ref(false)
const saving = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({ id: 0, topic: '', workflowId: undefined as number | undefined, workflowVersionId: undefined as number | undefined, status: 'active' })

const rules: FormRules = {
  topic: [
    { required: true, message: '请输入 topic', trigger: 'blur' },
    { max: 255, message: 'topic 不超过 255 字', trigger: 'blur' }
  ],
  workflowVersionId: [{ required: true, message: '请选择绑定版本', trigger: 'change' }]
}

async function load() {
  loading.value = true
  try {
    const data = await pageSubscriptions(query)
    list.value = data.records
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onPage(p: number) {
  query.pageNo = p
  void load()
}

async function openForm(row?: MqttSubscription) {
  if (!workflows.value.length) {
    const w = await pageWorkflows({ pageNo: 1, pageSize: 100 })
    workflows.value = w.records
  }
  if (row) {
    form.id = row.id
    form.topic = row.topic
    form.workflowVersionId = row.workflowVersionId
    form.status = row.status
    // 反查版本所属流程
    versionOptions.value = []
    form.workflowId = undefined
    for (const w of workflows.value) {
      const vs = await pageVersions(w.id, { pageNo: 1, pageSize: 100 })
      if (vs.records.some((v) => v.id === row.workflowVersionId)) {
        form.workflowId = w.id
        versionOptions.value = vs.records
        break
      }
    }
  } else {
    form.id = 0
    form.topic = ''
    form.workflowId = undefined
    form.workflowVersionId = undefined
    form.status = 'active'
    versionOptions.value = []
  }
  formVisible.value = true
}

async function onWorkflowChange(wfId: number) {
  form.workflowVersionId = undefined
  const vs = await pageVersions(wfId, { pageNo: 1, pageSize: 100 })
  versionOptions.value = vs.records
}

async function onSave() {
  await formRef.value?.validate()
  saving.value = true
  try {
    const payload = { topic: form.topic.trim(), workflowVersionId: form.workflowVersionId!, status: form.status }
    if (form.id) {
      await updateSubscription(form.id, payload)
      ElMessage.success('已更新')
    } else {
      await createSubscription(payload)
      ElMessage.success('已创建')
    }
    formVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: MqttSubscription) {
  await ElMessageBox.confirm(`确认删除订阅「${row.topic}」？`, '删除确认', { type: 'warning' })
  await deleteSubscription(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.title { font-weight: 600; }
</style>
