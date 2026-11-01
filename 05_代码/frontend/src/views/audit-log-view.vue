<template>
  <el-card class="page-card">
    <div class="table-toolbar">
      <span class="title">审计日志（写操作留痕，仅 admin 可见）</span>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table v-loading="loading" :data="list" empty-text="暂无审计记录">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="userId" label="用户ID" width="90" />
      <el-table-column prop="action" label="动作" min-width="180" />
      <el-table-column prop="target" label="目标" min-width="140" />
      <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip />
      <el-table-column prop="ip" label="IP" width="120" />
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.createdAt) }}</template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination background layout="total, prev, pager, next" :total="total" :page-size="query.pageSize" :current-page="query.pageNo" @current-change="onPage" />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { pageAuditLogs } from '@/api/quota'
import { fmtTime } from '@/utils/format'
import type { AuditLog } from '@/types'

/** FE-7.1 审计日志基础列表（美化属 P2 增强，本期不做） */
const loading = ref(false)
const list = ref<AuditLog[]>([])
const total = ref(0)
const query = reactive({ pageNo: 1, pageSize: 20 })

async function load() {
  loading.value = true
  try {
    const data = await pageAuditLogs(query)
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

onMounted(load)
</script>

<style scoped>
.title { font-weight: 600; }
</style>
