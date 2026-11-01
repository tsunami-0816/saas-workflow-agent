<template>
  <el-dialog v-model="visible" title="自然语言生成流程草稿" width="560px" :close-on-click-modal="false">
    <el-form label-position="top">
      <el-form-item label="流程名称（可选）">
        <el-input v-model="form.workflowName" maxlength="64" placeholder="默认：NL 生成流程" />
      </el-form-item>
      <el-form-item label="用自然语言描述流程（≤2000 字）" required>
        <el-input
          v-model="form.text"
          type="textarea"
          :rows="5"
          maxlength="2000"
          show-word-limit
          placeholder="示例：收到工厂温度消息后，超过 80 度就调用告警接口，否则记录正常"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="loading" :disabled="!form.text.trim()" @click="onGenerate">生成草稿</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { nlDraft } from '@/api/workflow'

const emit = defineEmits<{ (e: 'generated'): void }>()
const router = useRouter()

const visible = ref(false)
const loading = ref(false)
const form = reactive({ text: '', workflowName: '' })

function open() {
  form.text = ''
  form.workflowName = ''
  visible.value = true
}

/** 调 NL→流程接口：LLM 生成 DSL → Schema 校验（带错重试 1 次在后端），成功为 draft 版本 */
async function onGenerate() {
  loading.value = true
  try {
    const version = await nlDraft({ text: form.text.trim(), workflowName: form.workflowName.trim() || undefined })
    ElMessage.success('草稿生成成功，已载入画布')
    visible.value = false
    emit('generated')
    router.push({ path: `/workflows/${version.workflowId}/edit`, query: { versionId: String(version.id) } })
  } finally {
    loading.value = false
  }
}

defineExpose({ open })
</script>
