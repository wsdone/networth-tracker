<template>
  <div class="expenses-page">
    <div class="page-header">
      <h2>收支概览</h2>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="quickMode = !quickMode" size="small">记账</el-button>
        <el-button :icon="Upload" @click="importDialogVisible = true" size="small">导入账单</el-button>
      </div>
    </div>

    <!-- 快速记账 -->
    <el-card shadow="hover" class="section-card" v-if="quickMode">
      <div class="quick-entry">
        <el-segmented v-model="quickForm.direction" :options="directionOptions" size="small" />
        <el-date-picker v-model="quickForm.date" type="date" value-format="YYYY-MM-DD" style="width: 140px" size="default" />
        <el-input v-model="quickForm.amount" placeholder="金额" type="number" class="quick-amount" />
        <el-select v-model="quickForm.category" class="quick-category" placeholder="分类">
          <el-option v-for="cat in currentCategories" :key="cat" :label="cat" :value="cat" />
        </el-select>
        <el-input v-model="quickForm.notes" placeholder="备注" class="quick-notes" />
        <el-button type="primary" @click="handleQuickAdd" :loading="submitting">记一笔</el-button>
      </div>
    </el-card>

    <!-- 收支仪表盘 -->
    <el-card shadow="hover" class="section-card" v-if="stats">
      <template #header>
        <div class="list-header">
          <span>收支统计</span>
          <el-select v-model="chartMode" size="small" style="width: 140px">
            <el-option label="本月日消费" value="daily" />
            <el-option label="月度趋势" value="monthly" />
            <el-option label="支出分类" value="category" />
            <el-option label="收入分类" value="income" />
            <el-option label="来源占比" value="source" />
          </el-select>
        </div>
      </template>
      <!-- 摘要卡片 -->
      <div class="summary-row">
        <div class="summary-item">
          <span class="summary-label">本月支出</span>
          <span class="summary-value expense-color">{{ formatMoney(stats.summary.month_expense) }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">本月收入</span>
          <span class="summary-value income-color">{{ formatMoney(stats.summary.month_income) }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">本月结余</span>
          <span class="summary-value" :class="stats.summary.month_net >= 0 ? 'income-color' : 'expense-color'">
            {{ formatMoney(stats.summary.month_net) }}
          </span>
        </div>
        <div class="summary-item">
          <span class="summary-label">日均支出</span>
          <span class="summary-value">{{ formatMoney(stats.summary.daily_avg_expense) }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">笔数</span>
          <span class="summary-value">{{ stats.summary.month_count }}</span>
        </div>
      </div>
      <!-- 图表 -->
      <div ref="chartRef" class="expense-chart"></div>
    </el-card>

    <!-- 收支列表 -->
    <el-card shadow="hover" class="section-card">
      <template #header>
        <div class="list-header">
          <span>收支记录</span>
          <div class="list-filters">
            <el-input v-model="searchKeyword" placeholder="搜索备注" clearable style="width: 150px" size="small" @clear="fetchExpenses" @keyup.enter="fetchExpenses">
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-segmented v-model="filterDirection" :options="filterOptions" size="small" @change="fetchExpenses" />
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始"
              end-placeholder="结束"
              value-format="YYYY-MM-DD"
              @change="fetchExpenses"
              class="date-picker"
            />
          </div>
        </div>
      </template>
      <!-- 桌面表格 -->
      <div class="table-scroll desktop-table">
        <el-table :data="filteredExpenses" stripe>
          <el-table-column prop="date" label="日期" width="100" />
          <el-table-column label="类型" width="60">
            <template #default="{ row }">
              <span :class="row.direction === 'income' ? 'income-color' : 'expense-color'">
                {{ row.direction === 'income' ? '收入' : '支出' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="category" label="分类" width="100">
            <template #default="{ row }">
              <el-tag size="small" :color="categoryStyle(row.category).bg" :style="{ color: categoryStyle(row.category).fg, borderColor: categoryStyle(row.category).bg }">{{ row.category }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="金额" align="right" width="110">
            <template #default="{ row }">
              <span :class="row.direction === 'income' ? 'income-color' : 'expense-color'">
                {{ row.direction === 'income' ? '+' : '-' }}{{ formatMoney(row.amount) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="notes" label="备注" min-width="150" />
          <el-table-column label="来源" width="70">
            <template #default="{ row }">
              <el-tag v-if="row.source === 'wechat'" size="small" type="success">微信</el-tag>
              <el-tag v-else-if="row.source === 'douyin'" size="small">抖音</el-tag>
              <el-tag v-else-if="row.source === 'alipay'" size="small" type="primary">支付宝</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="110" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="showEditDialog(row)">编辑</el-button>
              <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <!-- 手机卡片 -->
      <div class="mobile-cards">
        <div class="expense-card" v-for="e in filteredExpenses" :key="e.id">
          <div class="card-top">
            <div class="card-info">
              <el-tag size="small" :color="categoryStyle(e.category).bg" :style="{ color: categoryStyle(e.category).fg, borderColor: categoryStyle(e.category).bg }">{{ e.category }}</el-tag>
              <span class="card-date">{{ e.date }}</span>
              <span :class="e.direction === 'income' ? 'income-color' : 'expense-color'" style="font-size: 12px">
                {{ e.direction === 'income' ? '收入' : '支出' }}
              </span>
            </div>
            <div class="card-actions">
              <el-button link type="primary" size="small" @click="showEditDialog(e)">编辑</el-button>
              <el-popconfirm title="确定删除？" @confirm="handleDelete(e.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
          <div class="card-bottom">
            <span class="card-amount" :class="e.direction === 'income' ? 'income-color' : 'expense-color'">
              {{ e.direction === 'income' ? '+' : '-' }}{{ formatMoney(e.amount) }}
            </span>
            <span v-if="e.notes" class="card-notes">{{ e.notes }}</span>
          </div>
        </div>
        <el-empty v-if="!filteredExpenses.length" description="暂无记录" :image-size="60" />
      </div>
    </el-card>

    <!-- 导入账单对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入账单" width="500px" class="responsive-dialog">
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls,.pdf,.csv"
        :on-change="handleFileChange"
        :on-remove="() => importFile = null"
        drag
      >
        <el-icon style="font-size: 40px; color: #c0c4cc"><UploadFilled /></el-icon>
        <div style="margin-top: 8px">拖拽或点击上传账单文件</div>
        <template #tip>
          <div style="font-size: 12px; color: #909399; margin-top: 8px">
            支持微信(xlsx)、抖音(pdf)、支付宝(csv) 账单
          </div>
        </template>
      </el-upload>
      <div style="margin-top: 16px; display: flex; align-items: center; gap: 12px">
        <el-switch v-model="importDeduct" />
        <span style="font-size: 13px">从匹配账户扣减余额</span>
      </div>
      <div style="font-size: 12px; color: #909399; margin-top: 4px">关闭则仅记录消费，不影响账户余额（推荐）</div>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleImport" :loading="importing" :disabled="!importFile">导入</el-button>
      </template>
    </el-dialog>

    <!-- 编辑消费对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑记录" width="420px" class="responsive-dialog">
      <el-form :model="editForm" label-width="70px" label-position="top" class="mobile-form">
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="日期">
              <el-date-picker v-model="editForm.date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="金额">
              <el-input-number v-model="editForm.amount" :precision="2" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="方向">
              <el-select v-model="editForm.direction" style="width: 100%">
                <el-option label="支出" value="expense" />
                <el-option label="收入" value="income" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="分类">
              <el-select v-model="editForm.category" style="width: 100%">
                <el-option v-for="cat in allCategories" :key="cat" :label="cat" :value="cat" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="备注">
              <el-input v-model="editForm.notes" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEdit" :loading="editSubmitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, watch, nextTick, onBeforeUnmount, computed } from 'vue'
import { Plus, Upload, UploadFilled, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import api from '@/api'
import { formatMoney } from '@/utils/format'

const expenseCategories = ['餐饮', '交通', '购物', '住房', '娱乐', '医疗', '教育', '订阅', '其他']
const incomeCategories = ['工资', '奖金', '兼职', '投资', '红包', '退款', '转账', '其他']
const allCategories = [...new Set([...expenseCategories, ...incomeCategories])]

const directionOptions = [
  { label: '支出', value: 'expense' },
  { label: '收入', value: 'income' },
]
const filterOptions = [
  { label: '全部', value: '' },
  { label: '支出', value: 'expense' },
  { label: '收入', value: 'income' },
]

const currentCategories = computed(() =>
  quickForm.direction === 'income' ? incomeCategories : expenseCategories
)

const expenses = ref<any[]>([])
const filteredExpenses = computed(() => {
  if (!searchKeyword.value) return expenses.value
  const kw = searchKeyword.value.toLowerCase()
  return expenses.value.filter(e => (e.notes || '').toLowerCase().includes(kw) || (e.category || '').toLowerCase().includes(kw))
})
const quickMode = ref(true)
const submitting = ref(false)
const dateRange = ref<string[]>([])
const filterDirection = ref('')
const searchKeyword = ref('')
const quickForm = reactive({ amount: '', category: '餐饮', notes: '', direction: 'expense', date: new Date().toISOString().slice(0, 10) })

// Reset category when direction changes
watch(() => quickForm.direction, (val) => {
  quickForm.category = val === 'income' ? '工资' : '餐饮'
})

const importDialogVisible = ref(false)
const importing = ref(false)
const importFile = ref<File | null>(null)
const importDeduct = ref(false)

// Stats & chart
const stats = ref<any>(null)
const chartMode = ref('daily')
const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null

const CATEGORY_COLORS: Record<string, string> = {
  '餐饮': '#e6a23c',
  '购物': '#409eff',
  '交通': '#67c23a',
  '住房': '#f56c6c',
  '娱乐': '#9b59b6',
  '医疗': '#e74c3c',
  '教育': '#3498db',
  '订阅': '#1abc9c',
  '利息': '#e67e22',
  '工资': '#27ae60',
  '奖金': '#2ecc71',
  '兼职': '#16a085',
  '投资': '#1abc9c',
  '红包': '#f39c12',
  '退款': '#909399',
  '转账': '#bdc3c7',
  '其他': '#95a5a6',
}

function categoryStyle(cat: string) {
  const bg = CATEGORY_COLORS[cat] || '#95a5a6'
  return { bg, fg: '#fff' }
}

const SOURCE_COLORS: Record<string, string> = {
  'alipay': '#409eff',
  'wechat': '#67c23a',
  'douyin': '#e6a23c',
  'manual': '#95a5a6',
}

const SOURCE_LABELS: Record<string, string> = {
  'alipay': '支付宝',
  'wechat': '微信',
  'douyin': '抖音',
  'manual': '手动',
}

function handleFileChange(file: any) {
  importFile.value = file.raw || file
}

async function handleImport() {
  if (!importFile.value) return
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)
    formData.append('source', 'auto')
    formData.append('deduct', String(importDeduct.value))
    const { data } = await api.post('/import/bill', formData)
    ElMessage.success(`导入完成：成功 ${data.imported} 条，跳过重复 ${data.skipped} 条`)
    if (data.unmatched?.length) {
      ElMessage.warning(`未匹配账户的支付方式：${data.unmatched.join('、')}`)
    }
    importDialogVisible.value = false
    importFile.value = null
    await fetchExpenses()
    await fetchStats()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
  }
}

async function fetchExpenses() {
  const params: any = {}
  if (dateRange.value?.length === 2) {
    params.start_date = dateRange.value[0]
    params.end_date = dateRange.value[1]
  }
  if (filterDirection.value) {
    params.direction = filterDirection.value
  }
  const { data } = await api.get('/expenses', { params })
  expenses.value = data
}

async function fetchStats() {
  try {
    const { data } = await api.get('/expenses/stats', { params: { months: 6 } })
    stats.value = data
    await nextTick()
    renderChart()
  } catch {
    // ignore
  }
}

function renderChart() {
  if (!chartRef.value || !stats.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
  const s = stats.value
  let option: echarts.EChartsOption

  if (chartMode.value === 'daily') {
    const dates = s.daily_trend.map((d: any) => d.date.slice(5))
    const expenses_ = s.daily_trend.map((d: any) => d.expense || 0)
    const incomes = s.daily_trend.map((d: any) => d.income || 0)
    const avg = s.summary.daily_avg_expense
    option = {
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          let tip = params[0].name + '<br/>'
          for (const p of params) {
            tip += `${p.seriesName}: ¥${p.value.toFixed(2)}<br/>`
          }
          return tip
        },
      },
      legend: { data: ['支出', '收入'] },
      grid: { left: 50, right: 20, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11 } },
      yAxis: { type: 'value', axisLabel: { formatter: '¥{value}' } },
      series: [
        {
          name: '支出',
          type: 'bar',
          data: expenses_,
          itemStyle: { color: '#f56c6c', borderRadius: [4, 4, 0, 0] },
          markLine: {
            silent: true,
            data: [{ yAxis: avg, name: '日均支出', label: { formatter: `日均 ¥${avg}`, fontSize: 11 } }],
            lineStyle: { color: '#e6a23c', type: 'dashed' },
          },
        },
        {
          name: '收入',
          type: 'bar',
          data: incomes,
          itemStyle: { color: '#67c23a', borderRadius: [4, 4, 0, 0] },
        },
      ],
    }
  } else if (chartMode.value === 'monthly') {
    const months = s.monthly_trend.map((d: any) => d.month)
    const expTotals = s.monthly_trend.map((d: any) => d.expense || 0)
    const incTotals = s.monthly_trend.map((d: any) => d.income || 0)
    option = {
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          let tip = params[0].name + '<br/>'
          for (const p of params) {
            tip += `${p.seriesName}: ¥${p.value.toFixed(2)}<br/>`
          }
          return tip
        },
      },
      legend: { data: ['支出', '收入'] },
      grid: { left: 50, right: 20, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: months },
      yAxis: { type: 'value', axisLabel: { formatter: '¥{value}' } },
      series: [
        {
          name: '支出',
          type: 'bar',
          data: expTotals,
          itemStyle: { color: '#f56c6c', borderRadius: [4, 4, 0, 0] },
        },
        {
          name: '收入',
          type: 'bar',
          data: incTotals,
          itemStyle: { color: '#67c23a', borderRadius: [4, 4, 0, 0] },
        },
      ],
    }
  } else if (chartMode.value === 'category') {
    const data = s.category_dist.map((d: any) => ({
      name: d.category,
      value: d.total,
      itemStyle: { color: CATEGORY_COLORS[d.category] || '#95a5a6' },
    }))
    option = {
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => `${params.name}<br/>¥${params.value.toFixed(2)} (${params.percent}%)`,
      },
      legend: { bottom: 0, type: 'scroll' },
      series: [{
        type: 'pie', radius: ['40%', '70%'],
        label: { formatter: '{b}\n¥{c}', fontSize: 11 },
        data,
      }],
    }
  } else if (chartMode.value === 'income') {
    const data = (s.income_dist || []).map((d: any) => ({
      name: d.category,
      value: d.total,
      itemStyle: { color: CATEGORY_COLORS[d.category] || '#95a5a6' },
    }))
    if (!data.length) {
      data.push({ name: '暂无收入', value: 1, itemStyle: { color: '#dcdfe6' } })
    }
    option = {
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => params.name === '暂无收入' ? '暂无收入记录' : `${params.name}<br/>¥${params.value.toFixed(2)} (${params.percent}%)`,
      },
      legend: { bottom: 0 },
      series: [{
        type: 'pie', radius: ['40%', '70%'],
        label: { formatter: '{b}\n¥{c}', fontSize: 11 },
        data,
      }],
    }
  } else {
    const data = s.source_dist.map((d: any) => ({
      name: SOURCE_LABELS[d.source] || d.source,
      value: d.total,
      itemStyle: { color: SOURCE_COLORS[d.source] || '#95a5a6' },
    }))
    option = {
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => `${params.name}<br/>¥${params.value.toFixed(2)} (${params.percent}%)`,
      },
      legend: { bottom: 0 },
      series: [{
        type: 'pie', radius: ['40%', '70%'],
        label: { formatter: '{b}\n¥{c}', fontSize: 11 },
        data,
      }],
    }
  }
  chartInstance.setOption(option, true)
}

function handleResize() {
  chartInstance?.resize()
}

watch(chartMode, () => renderChart())

onMounted(() => {
  fetchExpenses()
  fetchStats()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})

async function handleQuickAdd() {
  if (!quickForm.amount) return ElMessage.warning('请输入金额')
  submitting.value = true
  try {
    await api.post('/expenses', {
      date: quickForm.date || new Date().toISOString().slice(0, 10),
      amount: parseFloat(quickForm.amount),
      currency: 'CNY',
      category: quickForm.category,
      direction: quickForm.direction,
      notes: quickForm.notes || null,
    })
    ElMessage.success('记录成功')
    quickForm.amount = ''
    quickForm.notes = ''
    await fetchExpenses()
    await fetchStats()
  } finally {
    submitting.value = false
  }
}

// --- Edit ---
const editDialogVisible = ref(false)
const editSubmitting = ref(false)
const editForm = reactive({ id: '', date: '', amount: 0, direction: 'expense', category: '', notes: '' })

function showEditDialog(row: any) {
  editForm.id = row.id
  editForm.date = row.date
  editForm.amount = row.amount
  editForm.direction = row.direction || 'expense'
  editForm.category = row.category
  editForm.notes = row.notes || ''
  editDialogVisible.value = true
}

async function handleEdit() {
  editSubmitting.value = true
  try {
    await api.put(`/expenses/${editForm.id}`, {
      date: editForm.date,
      amount: editForm.amount,
      direction: editForm.direction,
      category: editForm.category,
      notes: editForm.notes || null,
    })
    ElMessage.success('更新成功')
    editDialogVisible.value = false
    await fetchExpenses()
    await fetchStats()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '更新失败')
  } finally {
    editSubmitting.value = false
  }
}

async function handleDelete(id: string) {
  await api.delete(`/expenses/${id}`)
  ElMessage.success('删除成功')
  await fetchExpenses()
  await fetchStats()
}
</script>

<style scoped>
.expenses-page { max-width: 1200px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { font-size: 18px; color: #303133; }
.header-actions { display: flex; gap: 8px; }
.section-card { margin-bottom: 16px; }

.quick-entry { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.quick-amount { width: 120px; }
.quick-category { width: 120px; }
.quick-notes { flex: 1; min-width: 120px; }

.list-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.list-filters { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.date-picker { width: 260px; }

.summary-row {
  display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;
}
.summary-item {
  flex: 1; min-width: 90px; text-align: center; padding: 8px;
  background: #f5f7fa; border-radius: 8px;
}
.summary-label { display: block; font-size: 12px; color: #909399; margin-bottom: 4px; }
.summary-value { display: block; font-size: 18px; font-weight: 600; color: #303133; }

.expense-color { color: #f56c6c; }
.income-color { color: #67c23a; }

.expense-chart { width: 100%; height: 300px; }

.table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }

.mobile-cards { display: none; }
.desktop-table { display: block; }

.expense-card {
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}
.expense-card:last-child { border-bottom: none; }

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.card-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-date {
  font-size: 12px;
  color: #909399;
}

.card-bottom {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.card-amount {
  font-size: 17px;
  font-weight: 600;
}

.card-notes {
  font-size: 13px;
  color: #909399;
}

@media (max-width: 768px) {
  .mobile-cards { display: block; }
  .desktop-table { display: none; }
  .page-header h2 { font-size: 16px; }
  .quick-amount { width: 80px; }
  .quick-category { width: 90px; }
  .quick-notes { width: 100%; }
  .list-filters { flex-direction: column; align-items: stretch; }
  .date-picker { width: 100%; }
  .summary-row { gap: 8px; }
  .summary-item { min-width: 70px; padding: 6px; }
  .summary-value { font-size: 15px; }
  .expense-chart { height: 250px; }
}
</style>
