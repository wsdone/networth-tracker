<template>
  <div class="reports-page">
    <div class="page-header">
      <h2>报表中心</h2>
      <el-button type="primary" @click="generateSnapshot" :loading="generating" size="small">生成快照</el-button>
    </div>

    <!-- 净资产趋势图 -->
    <el-card shadow="hover" class="section-card">
      <template #header>
        <div class="chart-header">
          <span>净资产趋势</span>
          <el-radio-group v-model="trendDays" size="small" @change="fetchTrend">
            <el-radio-button :value="30">30天</el-radio-button>
            <el-radio-button :value="90">90天</el-radio-button>
            <el-radio-button :value="365">1年</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <div ref="trendChartRef" class="chart-box"></div>
    </el-card>

    <!-- 历史快照列表 -->
    <el-card shadow="hover" class="section-card">
      <template #header><span>历史快照</span></template>
      <div class="table-scroll">
        <el-table :data="snapshots" stripe>
          <el-table-column prop="date" label="日期" width="100" />
          <el-table-column label="总资产" align="right" min-width="110">
            <template #default="{ row }">{{ formatMoney(row.total_assets_cny) }}</template>
          </el-table-column>
          <el-table-column label="总负债" align="right" min-width="110">
            <template #default="{ row }">{{ formatMoney(row.total_liabilities_cny) }}</template>
          </el-table-column>
          <el-table-column label="净资产" align="right" min-width="110">
            <template #default="{ row }">{{ formatMoney(row.net_worth_cny) }}</template>
          </el-table-column>
          <el-table-column label="当日盈亏" align="right" min-width="110">
            <template #default="{ row }">
              <span :class="row.daily_pnl_cny >= 0 ? 'text-red' : 'text-green'">{{ formatMoney(row.daily_pnl_cny) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import api from '@/api'
import { formatMoney } from '@/utils/format'
import type { Snapshot, TrendPoint } from '@/types'

const generating = ref(false)
const trendDays = ref(90)
const trendData = ref<TrendPoint[]>([])
const snapshots = ref<Snapshot[]>([])
const trendChartRef = ref<HTMLElement>()

async function fetchSnapshots() {
  const { data } = await api.get('/snapshots', { params: { limit: 90 } })
  snapshots.value = data
}

async function fetchTrend() {
  const { data } = await api.get('/dashboard/trend', { params: { days: trendDays.value } })
  trendData.value = data
  await nextTick()
  renderTrendChart()
}

function renderTrendChart() {
  if (!trendChartRef.value || !trendData.value.length) return
  const chart = echarts.init(trendChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['总资产', '总负债', '净资产'] },
    grid: { left: 55, right: 10, top: 40, bottom: 30 },
    xAxis: {
      type: 'category',
      data: trendData.value.map(d => d.date),
      axisLabel: { rotate: 30, fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 10,
        formatter: (v: number) => v >= 10000 ? `${(v / 10000).toFixed(0)}万` : v.toFixed(0),
      },
    },
    series: [
      { name: '总资产', type: 'line', smooth: true, data: trendData.value.map(d => d.total_assets_cny), lineStyle: { width: 2 } },
      { name: '总负债', type: 'line', smooth: true, data: trendData.value.map(d => d.total_liabilities_cny), lineStyle: { width: 2 }, itemStyle: { color: '#f56c6c' } },
      { name: '净资产', type: 'line', smooth: true, data: trendData.value.map(d => d.net_worth_cny), areaStyle: { opacity: 0.1 }, lineStyle: { width: 2 }, itemStyle: { color: '#409eff' } },
    ],
  })
}

async function generateSnapshot() {
  generating.value = true
  try {
    await api.post('/snapshots/generate')
    ElMessage.success('快照已生成')
    await fetchSnapshots()
    await fetchTrend()
  } finally {
    generating.value = false
  }
}

onMounted(async () => {
  await fetchSnapshots()
  await fetchTrend()
})
</script>

<style scoped>
.reports-page { max-width: 1400px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { font-size: 18px; color: #303133; }
.section-card { margin-bottom: 16px; }
.chart-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.chart-box { height: 320px; }
.table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.text-red { color: #f56c6c; }
.text-green { color: #67c23a; }

@media (max-width: 768px) {
  .page-header h2 { font-size: 16px; }
  .chart-box { height: 240px; }
  .chart-header { font-size: 14px; }
}
</style>
