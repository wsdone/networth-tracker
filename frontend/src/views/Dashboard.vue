<template>
  <div class="dashboard">
    <div class="page-header">
      <h2>仪表盘</h2>
      <el-button type="primary" :icon="Refresh" @click="refreshData" :loading="loading" size="small">刷新</el-button>
    </div>

    <!-- 概览卡片 -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-label">总资产</div>
        <div class="stat-value">{{ formatMoney(overview?.total_assets_cny) }}</div>
      </div>
      <div class="stat-card liability">
        <div class="stat-label">总负债</div>
        <div class="stat-value">{{ formatMoney(overview?.total_liabilities_cny) }}</div>
      </div>
      <div class="stat-card networth">
        <div class="stat-label">净资产</div>
        <div class="stat-value">{{ formatMoney(overview?.net_worth_cny) }}</div>
      </div>
      <div class="stat-card" :class="overview?.daily_pnl_cny && overview.daily_pnl_cny >= 0 ? 'positive' : 'negative'">
        <div class="stat-label">今日盈亏</div>
        <div class="stat-value">{{ formatMoney(overview?.daily_pnl_cny) }}</div>
      </div>
    </div>

    <!-- 多币种概览 -->
    <el-card shadow="hover" class="section-card" v-if="overview?.total_assets_by_currency">
      <template #header><span>多币种资产概览</span></template>
      <div class="table-scroll">
        <el-table :data="currencyData" stripe>
          <el-table-column label="币种" width="80">
            <template #default="{ row }">{{ row.currency_name || row.currency }}</template>
          </el-table-column>
          <el-table-column label="原币金额" align="right" min-width="100">
            <template #default="{ row }">{{ formatNumber(row.assets) }}</template>
          </el-table-column>
          <el-table-column label="折合人民币" align="right" min-width="120">
            <template #default="{ row }">{{ formatMoney(row.assets_cny) }}</template>
          </el-table-column>
          <el-table-column label="汇率" align="right" width="80">
            <template #default="{ row }">{{ row.rate ? formatNumber(row.rate, 4) : '-' }}</template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 图表区 -->
    <el-row :gutter="16">
      <el-col :xs="24" :sm="24" :md="12">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="chart-header">
              <span>资产分布</span>
              <el-radio-group v-model="assetDistBy" size="small" @change="handleAssetDistChange">
                <el-radio-button value="type">类型</el-radio-button>
                <el-radio-button value="account">账户</el-radio-button>
                <el-radio-button value="group">分组</el-radio-button>
                <el-radio-button value="tag">标签</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="distributionChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12">
        <el-card shadow="hover" class="section-card">
          <template #header><span>净资产趋势</span></template>
          <div ref="trendChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第二行图表 -->
    <el-row :gutter="16">
      <el-col :xs="24" :sm="24" :md="12">
        <el-card shadow="hover" class="section-card">
          <template #header><span>负债分布</span></template>
          <div ref="liabilityChartRef" class="chart-box"></div>
          <el-empty v-if="!liabilityDist.length" description="暂无负债" :image-size="60" />
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12">
        <el-card shadow="hover" class="section-card">
          <template #header><span>资产 vs 负债趋势</span></template>
          <div ref="assetLiabChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第三行：月度收支趋势 -->
    <el-card shadow="hover" class="section-card">
      <template #header><span>月度收支趋势</span></template>
      <div ref="expenseTrendChartRef" class="chart-box"></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import api from '@/api'
import { formatMoney, formatNumber } from '@/utils/format'
import type { Overview, CurrencyOverviewItem, AssetDistributionItem, TrendPoint } from '@/types'

const loading = ref(false)
const overview = ref<Overview | null>(null)
const distribution = ref<AssetDistributionItem[]>([])
const liabilityDist = ref<AssetDistributionItem[]>([])
const currencyData = ref<CurrencyOverviewItem[]>([])
const trendData = ref<TrendPoint[]>([])
const assetDistBy = ref('type')

const distributionChartRef = ref<HTMLElement>()
const trendChartRef = ref<HTMLElement>()
const liabilityChartRef = ref<HTMLElement>()
const assetLiabChartRef = ref<HTMLElement>()
const expenseTrendChartRef = ref<HTMLElement>()

let distributionChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null
let liabilityChart: echarts.ECharts | null = null
let assetLiabChart: echarts.ECharts | null = null
let expenseTrendChart: echarts.ECharts | null = null

const expenseTrendData = ref<any[]>([])

async function fetchOverview() {
  const { data } = await api.get('/dashboard/overview')
  overview.value = data
}

async function fetchDistribution() {
  const { data } = await api.get('/dashboard/asset-distribution', { params: { by: assetDistBy.value } })
  distribution.value = data
}

async function fetchLiabilityDist() {
  const { data } = await api.get('/dashboard/liability-distribution')
  liabilityDist.value = data
}

async function fetchCurrencyOverview() {
  const { data } = await api.get('/dashboard/currency-overview')
  currencyData.value = data
}

async function fetchTrend() {
  const { data } = await api.get('/dashboard/trend', { params: { days: 90 } })
  trendData.value = data
}

async function fetchExpenseTrend() {
  const { data } = await api.get('/dashboard/expense-trend', { params: { months: 6 } })
  expenseTrendData.value = data
}

async function handleAssetDistChange() {
  await fetchDistribution()
  renderDistributionChart()
}

function renderDistributionChart() {
  if (!distributionChartRef.value || !distribution.value.length) return
  if (!distributionChart) {
    distributionChart = echarts.init(distributionChartRef.value)
  }
  distributionChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => `${params.name}: ${formatMoney(params.value)} (${params.percent}%)`,
    },
    series: [{
      type: 'pie',
      radius: ['35%', '65%'],
      label: { formatter: '{b}\n{d}%', fontSize: 12 },
      data: distribution.value.map(item => ({
        name: item.name,
        value: Math.round(item.value_cny * 100) / 100,
      })),
    }],
  })
}

function renderTrendChart() {
  if (!trendChartRef.value || !trendData.value.length) return
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 10, top: 10, bottom: 30 },
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
    series: [{
      name: '净资产',
      type: 'line',
      smooth: true,
      data: trendData.value.map(d => d.net_worth_cny),
      areaStyle: { opacity: 0.1 },
      lineStyle: { width: 2 },
      itemStyle: { color: '#409eff' },
    }],
  })
}

function renderLiabilityChart() {
  if (!liabilityChartRef.value) return
  if (!liabilityChart) {
    liabilityChart = echarts.init(liabilityChartRef.value)
  }
  if (!liabilityDist.value.length) {
    liabilityChart.clear()
    return
  }
  liabilityChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => `${params.name}: ${formatMoney(params.value)} (${params.percent}%)`,
    },
    series: [{
      type: 'pie',
      radius: ['35%', '65%'],
      label: { formatter: '{b}\n{d}%', fontSize: 12 },
      data: liabilityDist.value.map(item => ({
        name: item.name,
        value: Math.round(item.value_cny * 100) / 100,
      })),
      itemStyle: {
        color: (params: any) => {
          const colors = ['#e6a23c', '#f56c6c', '#909399', '#b37feb']
          return colors[params.dataIndex % colors.length]
        },
      },
    }],
  })
}

function renderAssetLiabChart() {
  if (!assetLiabChartRef.value || !trendData.value.length) return
  if (!assetLiabChart) {
    assetLiabChart = echarts.init(assetLiabChartRef.value)
  }
  assetLiabChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['总资产', '总负债'], top: 0, textStyle: { fontSize: 11 } },
    grid: { left: 60, right: 10, top: 30, bottom: 30 },
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
      {
        name: '总资产',
        type: 'line',
        smooth: true,
        data: trendData.value.map(d => Math.round(d.total_assets_cny * 100) / 100),
        lineStyle: { width: 2 },
        itemStyle: { color: '#409eff' },
        areaStyle: { opacity: 0.05 },
      },
      {
        name: '总负债',
        type: 'line',
        smooth: true,
        data: trendData.value.map(d => Math.round(d.total_liabilities_cny * 100) / 100),
        lineStyle: { width: 2 },
        itemStyle: { color: '#e6a23c' },
        areaStyle: { opacity: 0.05 },
      },
    ],
  })
}

function renderExpenseTrendChart() {
  if (!expenseTrendChartRef.value || !expenseTrendData.value.length) return
  if (!expenseTrendChart) {
    expenseTrendChart = echarts.init(expenseTrendChartRef.value)
  }
  expenseTrendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['支出', '收入'], top: 0, textStyle: { fontSize: 11 } },
    grid: { left: 60, right: 10, top: 30, bottom: 30 },
    xAxis: {
      type: 'category',
      data: expenseTrendData.value.map(d => d.month),
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 10,
        formatter: (v: number) => v >= 10000 ? `${(v / 10000).toFixed(0)}万` : v.toFixed(0),
      },
    },
    series: [
      {
        name: '支出',
        type: 'bar',
        data: expenseTrendData.value.map(d => d.expense),
        itemStyle: { color: '#f56c6c' },
        barMaxWidth: 30,
      },
      {
        name: '收入',
        type: 'bar',
        data: expenseTrendData.value.map(d => d.income),
        itemStyle: { color: '#67c23a' },
        barMaxWidth: 30,
      },
    ],
  })
}

async function refreshData() {
  loading.value = true
  try {
    try { await api.post('/market/refresh') } catch {}
    try { await api.post('/market/refresh-rates') } catch {}
    await fetchOverview()
    await fetchDistribution()
    await fetchLiabilityDist()
    await fetchCurrencyOverview()
    await fetchTrend()
    await fetchExpenseTrend()
    await nextTick()
    renderDistributionChart()
    renderTrendChart()
    renderLiabilityChart()
    renderAssetLiabChart()
    renderExpenseTrendChart()
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await refreshData()
})
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h2 {
  font-size: 18px;
  color: #303133;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px 12px;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.stat-card .stat-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
  white-space: nowrap;
}

.stat-card .stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  word-break: break-all;
  line-height: 1.3;
}

.stat-card.networth .stat-value { color: #409eff; }
.stat-card.positive .stat-value { color: #f56c6c; }
.stat-card.negative .stat-value { color: #67c23a; }
.stat-card.liability .stat-value { color: #e6a23c; }

.section-card {
  margin-bottom: 12px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.chart-box {
  height: 280px;
}

.table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

@media (max-width: 768px) {
  .page-header h2 { font-size: 16px; }

  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }

  .stat-card {
    padding: 12px 8px;
  }

  .stat-card .stat-label { font-size: 11px; }
  .stat-card .stat-value { font-size: 15px; }

  .chart-box { height: 240px; }

  .chart-header {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 380px) {
  .stat-card .stat-value { font-size: 13px; }
}
</style>
