<template>
  <el-card class="page-card">
    <div class="table-toolbar">
      <div>
        <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 160px" @change="onSearch">
          <el-option v-for="s in ['RUNNING', 'SUCCESS', 'FAILED', 'WAITING']" :key="s" :value="s" :label="EXEC_STATUS_TEXT[s]" />
        </el-select>
        <el-button type="primary" style="margin-left: 8px" @click="onSearch">查询</el-button>
      </div>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table v-loading="loading" :data="list" empty-text="暂无执行记录">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="versionId" label="版本ID" width="90" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)">{{ EXEC_STATUS_TEXT[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="triggerType" label="触发方式" width="100" />
      <el-table-column label="失败原因" min-width="140">
        <template #default="{ row }">{{ row.failReason ? FAIL_REASON_TEXT[row.failReason] || row.failReason : '-' }}</template>
      </el-table-column>
      <el-table-column label="开始时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.startedAt) }}</template>
      </el-table-column>
      <el-table-column label="结束时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.endedAt) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push(`/executions/${row.id}`)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination background layout="total, prev, pager, next" :total="total" :page-size="query.pageSize" :current-page="query.pageNo" @current-change="onPage" />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { pageExecutions } from '@/api/execution'
import { EXEC_STATUS_TEXT, FAIL_REASON_TEXT, fmtTime, statusTagType } from '@/utils/format'
import type { Execution } from '@/types'

const router = useRouter()
const loading = ref(false)
const list = ref<Execution[]>([])
const total = ref(0)
const query = reactive({ pageNo: 1, pageSize: 20, status: '' })

async function load() {
  loading.value = true
  try {
    const data = await pageExecutions({ ...query, status: query.status || undefined })
    list.value = data.records
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onSearch() {
  query.pageNo = 1
  void load()
}

function onPage(p: number) {
  query.pageNo = p
  void load()
}

onMounted(load)
</script>
