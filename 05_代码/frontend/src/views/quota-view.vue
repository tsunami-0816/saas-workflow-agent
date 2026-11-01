<template>
  <div>
    <el-card class="page-card">
      <div class="table-toolbar"><span class="title">租户额度</span></div>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="租户ID">{{ quota?.tenantId ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="Token 总额度">{{ quota?.tokenTotal ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="已使用">{{ quota?.tokenUsed ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="实时剩余（Redis）">
          <span :class="{ danger: lowRemain }">{{ quota?.remain ?? '-' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="使用率" :span="2">
          <el-progress :percentage="usagePercent" :status="lowRemain ? 'exception' : undefined" />
        </el-descriptions-item>
      </el-descriptions>
      <el-alert v-if="lowRemain" type="warning" :closable="false" style="margin-top: 12px" title="额度剩余不足 10%，超额调用将返回 429，请联系管理员调整额度" />
    </el-card>

    <el-card class="page-card">
      <div class="table-toolbar"><span class="title">LLM 调用台账（token × 单价成本）</span></div>
      <el-table v-loading="loading" :data="list" empty-text="暂无调用记录">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="provider" label="Provider" width="110" />
        <el-table-column prop="model" label="Model" min-width="140" />
        <el-table-column prop="taskType" label="taskType" width="140" />
        <el-table-column prop="promptTokens" label="Prompt Tokens" width="120" />
        <el-table-column prop="completionTokens" label="Completion Tokens" width="140" />
        <el-table-column label="成本(元)" width="100">
          <template #default="{ row }">{{ row.cost }}</template>
        </el-table-column>
        <el-table-column prop="latencyMs" label="耗时(ms)" width="90" />
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ fmtTime(row.createdAt) }}</template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination background layout="total, prev, pager, next" :total="total" :page-size="query.pageSize" :current-page="query.pageNo" @current-change="onPage" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { getQuota, pageLlmCalls } from '@/api/quota'
import { fmtTime } from '@/utils/format'
import type { LlmCallLog, Quota } from '@/types'

const quota = ref<Quota | null>(null)
const loading = ref(false)
const list = ref<LlmCallLog[]>([])
const total = ref(0)
const query = reactive({ pageNo: 1, pageSize: 20 })

const usagePercent = computed(() => {
  if (!quota.value || !quota.value.tokenTotal) return 0
  return Math.min(100, Math.round((quota.value.tokenUsed / quota.value.tokenTotal) * 100))
})
const lowRemain = computed(() => !!quota.value && quota.value.tokenTotal > 0 && quota.value.remain / quota.value.tokenTotal < 0.1)

async function load() {
  loading.value = true
  try {
    const [q, logs] = await Promise.all([getQuota(), pageLlmCalls(query)])
    quota.value = q
    list.value = logs.records
    total.value = logs.total
  } finally {
    loading.value = false
  }
}

function onPage(p: number) {
  query.pageNo = p
  void load()
}

onMounted(load)
</script>

<style scoped>
.title { font-weight: 600; }
.danger { color: #f56c6c; font-weight: 600; }
</style>
