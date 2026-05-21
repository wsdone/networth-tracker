<template>
  <div class="settings-page">
    <div class="page-header"><h2>系统设置</h2></div>

    <el-card shadow="hover" class="section-card">
      <template #header><span>汇率管理</span></template>
      <el-button type="primary" @click="refreshRates" :loading="refreshing" size="small">刷新汇率</el-button>
      <div class="table-scroll">
        <el-table :data="rates" stripe style="margin-top: 12px">
          <el-table-column prop="base_currency" label="基准" width="80" />
          <el-table-column prop="quote_currency" label="目标" width="80" />
          <el-table-column label="汇率" align="right" min-width="100">
            <template #default="{ row }">{{ parseFloat(row.rate).toFixed(4) }}</template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" min-width="150" />
        </el-table>
      </div>
    </el-card>

    <el-card shadow="hover" class="section-card">
      <template #header><span>数据导出</span></template>
      <div class="export-buttons">
        <el-button @click="exportData('accounts')" size="small">导出账户</el-button>
        <el-button @click="exportData('holdings')" size="small">导出持仓</el-button>
        <el-button @click="exportData('transactions')" size="small">导出交易</el-button>
        <el-button @click="exportData('snapshots')" size="small">导出快照</el-button>
      </div>
    </el-card>

    <el-card shadow="hover" class="section-card">
      <template #header><span>数据备份与恢复</span></template>
      <div class="backup-section">
        <div class="backup-row">
          <span>下载当前数据库完整备份（SQLite 文件）</span>
          <el-button type="primary" @click="downloadBackup" :loading="backupLoading" size="small">下载数据库备份</el-button>
        </div>
        <el-divider />
        <div class="backup-row">
          <span>从备份文件恢复数据库（需要重启服务）</span>
          <el-upload
            :auto-upload="false"
            :limit="1"
            accept=".db"
            :on-change="handleRestoreFile"
            :show-file-list="false"
          >
            <el-button type="warning" size="small">上传备份恢复</el-button>
          </el-upload>
        </div>
        <div style="font-size: 12px; color: #909399; margin-top: 4px">恢复前会自动备份当前数据库，恢复后需要重启后端服务</div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const rates = ref<any[]>([])
const refreshing = ref(false)
const backupLoading = ref(false)

async function fetchRates() {
  const { data } = await api.get('/market/exchange-rates')
  rates.value = data
}

async function refreshRates() {
  refreshing.value = true
  try {
    await api.post('/market/refresh-rates')
    ElMessage.success('汇率已刷新')
    await fetchRates()
  } finally {
    refreshing.value = false
  }
}

async function exportData(type: string) {
  try {
    const { data } = await api.get(`/export/${type}`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `${type}_${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
  } catch {
    ElMessage.info('导出功能将在后续版本中实现')
  }
}

async function downloadBackup() {
  backupLoading.value = true
  try {
    const { data } = await api.get('/backup/backup', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `wallet_backup_${new Date().toISOString().slice(0, 10)}.db`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('备份下载成功')
  } catch {
    ElMessage.error('下载备份失败')
  } finally {
    backupLoading.value = false
  }
}

async function handleRestoreFile(uploadFile: any) {
  try {
    await ElMessageBox.confirm('恢复数据库将覆盖当前所有数据，恢复后需要重启服务。确定继续？', '确认恢复', { type: 'warning' })
    const formData = new FormData()
    formData.append('file', uploadFile.raw)
    await api.post('/backup/restore', formData)
    ElMessage.success('数据库已恢复，请重启后端服务')
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('恢复失败')
  }
}

onMounted(fetchRates)
</script>

<style scoped>
.settings-page { max-width: 900px; }
.page-header { margin-bottom: 16px; }
.page-header h2 { font-size: 18px; color: #303133; }
.section-card { margin-bottom: 16px; }
.table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.export-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
.backup-section { }
.backup-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.backup-row span { font-size: 14px; color: #606266; }

@media (max-width: 768px) {
  .page-header h2 { font-size: 16px; }
}
</style>
