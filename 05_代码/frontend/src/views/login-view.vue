<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2 class="title">SaaS 工作流编排平台</h2>
      <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="onSubmit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" maxlength="64" autofocus />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" maxlength="64" show-password @keyup.enter="onSubmit" />
        </el-form-item>
        <el-button class="submit" type="primary" :loading="loading" @click="onSubmit">登 录</el-button>
      </el-form>
      <div class="tip">Mock 种子账号：admin_acme / dev_acme / viewer_acme，密码 Swa@123456</div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function onSubmit() {
  await formRef.value?.validate()
  loading.value = true
  try {
    const data = await login(form)
    // JWT 存 localStorage；tenantId 一律由后端 token claim 决定，前端不传
    auth.setSession(data.token, { userId: data.userId, tenantId: data.tenantId, username: data.username, role: data.role })
    ElMessage.success(`欢迎，${data.username}`)
    router.push((route.query.redirect as string) || '/workflows')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { height: 100%; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #1f2d3d, #2f80ed); }
.login-card { width: 380px; }
.title { text-align: center; margin: 8px 0 24px; }
.submit { width: 100%; }
.tip { margin-top: 16px; color: #909399; font-size: 12px; text-align: center; }
</style>
