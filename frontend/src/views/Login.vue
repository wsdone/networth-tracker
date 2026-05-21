<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <el-icon :size="36" color="#409eff"><Wallet /></el-icon>
        <h1>资产管理</h1>
        <p>请输入密码解锁</p>
      </div>
      <el-form @submit.prevent="handleLogin">
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            placeholder="输入密码"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" @click="handleLogin" :loading="loading">
          解锁
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Wallet } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const router = useRouter()
const password = ref('')
const loading = ref(false)

async function handleLogin() {
  if (!password.value) return
  loading.value = true
  try {
    const { data } = await api.post('/auth/login', { password: password.value })
    if (data.token) {
      localStorage.setItem('auth_token', data.token)
    }
    router.replace('/')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  width: 360px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h1 {
  font-size: 22px;
  color: #303133;
  margin: 12px 0 4px;
}

.login-header p {
  font-size: 14px;
  color: #909399;
}
</style>
