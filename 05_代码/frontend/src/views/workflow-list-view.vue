<template>
  <el-card class="page-card">
    <div class="table-toolbar">
      <div>
        <el-input v-model="query.name" placeholder="按名称搜索" clearable style="width: 240px" maxlength="64" @keyup.enter="onSearch" @clear="onSearch" />
        <el-button type="primary" style="margin-left: 8px" @click="onSearch">搜索</el-button>
      </div>
      <div v-if="auth.canWrite">
        <el-button @click="nlDialogRef?.open()">NL 生成流程</el-button>
        <el-button type="primary" @click="openCreate">新建流程</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="list" :empty-text="emptyText">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="名称" min-width="180" />
      <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
      <el-table-column label="更新时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.updatedAt) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="260">
        <template #default="{ row }">
          <el-button link type="primary" @click="versionDrawerRef?.open(row.id, row.name)">版本</el-button>
          <el-button link type="primary" @click="openEditor(row)">画布</el-button>
          <template v-if="auth.canWrite">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination background layout="total, prev, pager, next" :total="total" :page-size="query.pageSize" :current-page="query.pageNo" @current-change="onPage" />
    </div>

    <!-- 新建/编辑流程 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑流程' : '新建流程'" width="480px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="255" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>

    <VersionManageDrawer ref="versionDrawerRef" />
    <NlDraftDialog ref="nlDialogRef" @generated="load" />
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { createWorkflow, deleteWorkflow, pageWorkflows, updateWorkflow } from '@/api/workflow'
import { fmtTime } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import type { Workflow } from '@/types'
import VersionManageDrawer from '@/components/version-manage-drawer.vue'
import NlDraftDialog from '@/components/nl-draft-dialog.vue'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(false)
const list = ref<Workflow[]>([])
const total = ref(0)
const query = reactive({ pageNo: 1, pageSize: 20, name: '' })
const searched = ref(false)

/** FE-3.1：空态与搜索无结果态区分文案 */
const emptyText = computed(() => (searched.value && query.name ? `未找到名称包含「${query.name}」的流程` : '暂无流程，点击右上角「新建流程」开始'))

const versionDrawerRef = ref<InstanceType<typeof VersionManageDrawer>>()
const nlDialogRef = ref<InstanceType<typeof NlDraftDialog>>()

const formVisible = ref(false)
const saving = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({ id: 0, name: '', description: '' })
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入名称', trigger: 'blur' },
    { max: 64, message: '名称不超过 64 字', trigger: 'blur' }
  ]
}

async function load() {
  loading.value = true
  try {
    const data = await pageWorkflows({ ...query, name: query.name || undefined })
    list.value = data.records
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onSearch() {
  searched.value = true
  query.pageNo = 1
  void load()
}

function onPage(p: number) {
  query.pageNo = p
  void load()
}

function openCreate() {
  form.id = 0
  form.name = ''
  form.description = ''
  formVisible.value = true
}

function openEdit(row: Workflow) {
  form.id = row.id
  form.name = row.name
  form.description = row.description
  formVisible.value = true
}

async function onSave() {
  await formRef.value?.validate()
  saving.value = true
  try {
    if (form.id) {
      await updateWorkflow(form.id, { name: form.name.trim(), description: form.description.trim() })
      ElMessage.success('已更新')
    } else {
      await createWorkflow({ name: form.name.trim(), description: form.description.trim() })
      ElMessage.success('已创建，请进入画布编排节点')
    }
    formVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

/** FE-3.1：删除二次确认 */
async function onDelete(row: Workflow) {
  await ElMessageBox.confirm(`确认删除流程「${row.name}」？其全部版本将不可再执行。`, '删除确认', { type: 'warning', confirmButtonText: '删除', confirmButtonClass: 'el-button--danger' })
  await deleteWorkflow(row.id)
  ElMessage.success('已删除')
  await load()
}

function openEditor(row: Workflow) {
  router.push(`/workflows/${row.id}/edit`)
}

onMounted(load)
</script>
