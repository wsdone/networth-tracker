<template>
  <div class="holdings-page">
    <div class="page-header">
      <h2>持仓管理</h2>
      <div class="header-actions">
        <el-button :icon="Refresh" @click="refreshQuotes" :loading="refreshing" size="small">刷新行情</el-button>
        <el-button type="primary" :icon="Plus" @click="showHoldingDialog()" size="small">添加持仓</el-button>
      </div>
    </div>

    <!-- 桌面端表格 -->
    <el-card shadow="hover" class="desktop-table">
      <div class="table-scroll">
        <el-table :data="holdings" stripe>
          <el-table-column prop="symbol" label="代码" width="90" />
          <el-table-column prop="name" label="名称" min-width="100" />
          <el-table-column label="账户" width="100">
            <template #default="{ row }">{{ accountNameMap[row.account_id] || '--' }}</template>
          </el-table-column>
          <el-table-column label="类型" width="70">
            <template #default="{ row }">
              {{ assetTypeLabels[row.asset_type] }}
              <el-tag v-if="row.quantity < 0" size="small" type="danger">空</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="数量" align="right" width="90">
            <template #default="{ row }">
              <span :class="row.quantity < 0 ? 'text-green' : ''">{{ formatNumber(row.quantity, row.asset_type === 'fund' ? 2 : 0) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="成本" align="right" width="90">
            <template #default="{ row }">{{ formatNumber(row.cost_price) }}</template>
          </el-table-column>
          <el-table-column label="现价" align="right" width="90">
            <template #default="{ row }">{{ row.market_price ? formatNumber(row.market_price) : '--' }}</template>
          </el-table-column>
          <el-table-column label="市值" align="right" width="110">
            <template #default="{ row }">{{ row.market_value ? formatMoney(row.market_value, row.currency) : '--' }}</template>
          </el-table-column>
          <el-table-column label="盈亏" align="right" width="110">
            <template #default="{ row }">
              <span v-if="row.pnl != null" :class="row.pnl >= 0 ? 'text-red' : 'text-green'">
                {{ formatMoney(row.pnl, row.currency) }}
              </span>
              <span v-else>--</span>
            </template>
          </el-table-column>
          <el-table-column label="盈亏%" align="right" width="80">
            <template #default="{ row }">
              <span v-if="row.pnl_pct != null" :class="row.pnl_pct >= 0 ? 'text-red' : 'text-green'">
                {{ formatPct(row.pnl_pct) }}
              </span>
              <span v-else>--</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="showHoldingDialog(row)">编辑</el-button>
              <el-button link type="primary" @click="showTransactionDialog(row)">交易</el-button>
              <el-button link type="primary" @click="viewTransactions(row)">记录</el-button>
              <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
                <template #reference>
                  <el-button link type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 手机端卡片列表 -->
    <div class="mobile-cards">
      <div class="holding-card" v-for="h in holdings" :key="h.id">
        <div class="card-top">
          <div class="card-title">
            <span class="card-symbol">{{ h.symbol }}</span>
            <span class="card-name">{{ h.name }}</span>
            <el-tag size="small" class="card-type">{{ assetTypeLabels[h.asset_type] }}</el-tag>
            <span class="card-acc">{{ accountNameMap[h.account_id] }}</span>
          </div>
          <div class="card-actions">
            <el-button link type="primary" size="small" @click="showHoldingDialog(h)">编辑</el-button>
            <el-button link type="primary" size="small" @click="showTransactionDialog(h)">交易</el-button>
            <el-button link type="primary" size="small" @click="viewTransactions(h)">记录</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(h.id)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
        <div class="card-numbers">
          <div class="card-num">
            <span class="num-label">数量</span>
            <span class="num-value">{{ formatNumber(h.quantity, h.asset_type === 'fund' ? 2 : 0) }}</span>
          </div>
          <div class="card-num">
            <span class="num-label">成本</span>
            <span class="num-value">{{ formatNumber(h.cost_price) }}</span>
          </div>
          <div class="card-num">
            <span class="num-label">现价</span>
            <span class="num-value">{{ h.market_price ? formatNumber(h.market_price) : '--' }}</span>
          </div>
          <div class="card-num">
            <span class="num-label">市值</span>
            <span class="num-value">{{ h.market_value ? formatMoney(h.market_value, h.currency) : '--' }}</span>
          </div>
          <div class="card-num" v-if="h.pnl != null">
            <span class="num-label">盈亏</span>
            <span class="num-value" :class="h.pnl >= 0 ? 'text-red' : 'text-green'">
              {{ formatMoney(h.pnl, h.currency) }}
            </span>
          </div>
          <div class="card-num" v-if="h.pnl_pct != null">
            <span class="num-label">盈亏%</span>
            <span class="num-value" :class="h.pnl_pct >= 0 ? 'text-red' : 'text-green'">
              {{ formatPct(h.pnl_pct) }}
            </span>
          </div>
        </div>
      </div>
      <el-empty v-if="!holdings.length" description="暂无持仓" />
    </div>

    <!-- 添加持仓对话框 -->
    <el-dialog v-model="holdingDialogVisible" :title="editingHoldingId ? '编辑持仓' : '添加持仓'" width="500px" class="responsive-dialog">
      <el-form :model="holdingForm" label-width="90px" label-position="top" class="mobile-form">
        <el-form-item label="所属账户" required>
          <el-select v-model="holdingForm.account_id" style="width: 100%">
            <el-option v-for="acc in brokerAccounts" :key="acc.id" :label="`${acc.name} (${typeLabels[acc.type] || acc.type})`" :value="acc.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="代码" required>
              <el-input v-model="holdingForm.symbol" placeholder="股票:600519 期货:RB2610" :disabled="!!editingHoldingId" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="名称" required>
              <el-input v-model="holdingForm.name" placeholder="如 贵州茅台" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="资产类型" required>
              <el-select v-model="holdingForm.asset_type" style="width: 100%">
                <el-option label="股票" value="stock" />
                <el-option label="基金" value="fund" />
                <el-option label="债券" value="bond" />
                <el-option label="ETF" value="etf" />
                <el-option label="货币基金" value="money_fund" />
                <el-option label="期货" value="futures" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="币种">
              <el-select v-model="holdingForm.currency" style="width: 100%">
                <el-option label="人民币" value="CNY" />
                <el-option label="港币" value="HKD" />
                <el-option label="美元" value="USD" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="交易所">
          <el-select v-model="holdingForm.exchange" clearable style="width: 100%" @change="holdingForm.currency = autoCurrency(holdingForm.exchange)">
            <el-option label="沪市" value="SSE" />
            <el-option label="深市" value="SZSE" />
            <el-option label="港股" value="HKSE" />
            <el-option label="纽交所" value="NYSE" />
            <el-option label="纳斯达克" value="NASDAQ" />
            <el-option label="场外" value="OTC" />
            <el-option label="上期所" value="SHFE" />
            <el-option label="大商所" value="DCE" />
            <el-option label="郑商所" value="CZCE" />
            <el-option label="中金所" value="CFFEX" />
            <el-option label="能源中心" value="INE" />
            <el-option label="广期所" value="GFEX" />
          </el-select>
        </el-form-item>
        <template v-if="holdingForm.asset_type === 'futures'">
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="合约乘数">
                <el-input-number v-model="holdingForm.multiplier" :precision="0" :min="1" style="width: 100%" placeholder="如 螺纹钢10" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="占用保证金">
                <el-input-number v-model="holdingForm.margin_deposit" :precision="2" :min="0" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>
        </template>
        <el-divider>首笔交易信息（可选）</el-divider>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="成交价格">
              <el-input-number v-model="holdingForm.initial_buy_price" :precision="4" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数量(做空填负数)">
              <el-input-number v-model="holdingForm.quantity" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="买入日期">
              <el-date-picker v-model="holdingForm.initial_buy_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="手续费">
              <el-input-number v-model="holdingForm.initial_buy_fee" :precision="2" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="计入总资产">
          <el-switch v-model="holdingForm.include_in_total" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="holdingDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveHolding" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 添加交易对话框 -->
    <el-dialog v-model="txDialogVisible" title="添加交易" width="450px" class="responsive-dialog">
      <el-form :model="txForm" label-width="70px" label-position="top" class="mobile-form">
        <el-form-item label="持仓">
          <span>{{ selectedHolding?.symbol }} {{ selectedHolding?.name }}</span>
        </el-form-item>
        <el-form-item label="类型" required>
          <el-radio-group v-model="txForm.type">
            <el-radio value="buy">买入</el-radio>
            <el-radio value="sell">卖出</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="日期" required>
              <el-date-picker v-model="txForm.date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="价格" required>
              <el-input-number v-model="txForm.price" :precision="4" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="数量" required>
              <el-input-number v-model="txForm.quantity" :precision="2" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="手续费">
          <el-input-number v-model="txForm.fee" :precision="2" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="txForm.notes" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="txDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreateTx" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 交易记录对话框 -->
    <el-dialog v-model="txListDialogVisible" :title="`交易记录 - ${txListHolding?.symbol || ''}`" width="700px" class="responsive-dialog">
      <div class="table-scroll">
        <el-table :data="transactions" stripe>
          <el-table-column prop="date" label="日期" width="100" />
          <el-table-column prop="type" label="类型" width="70">
            <template #default="{ row }">
              <el-tag :type="row.type === 'buy' ? 'danger' : 'success'" size="small">{{ row.type === 'buy' ? '买入' : '卖出' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="价格" align="right" width="90">
            <template #default="{ row }">{{ formatNumber(row.price) }}</template>
          </el-table-column>
          <el-table-column label="数量" align="right" width="90">
            <template #default="{ row }">{{ formatNumber(row.quantity) }}</template>
          </el-table-column>
          <el-table-column label="金额" align="right" width="110">
            <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="70">
            <template #default="{ row }">
              <el-popconfirm title="确定删除？" @confirm="handleDeleteTx(row.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { formatMoney, formatNumber, formatPct } from '@/utils/format'
import type { Account, Holding, Transaction } from '@/types'

const assetTypeLabels: Record<string, string> = { stock: '股票', fund: '基金', bond: '债券', etf: 'ETF', money_fund: '货币基金', futures: '期货' }
const typeLabels: Record<string, string> = { bank: '银行卡', alipay: '支付宝', wechat: '微信', broker: '券商', overseas_bank: '境外银行', cash: '现金' }

const holdings = ref<Holding[]>([])
const brokerAccounts = ref<Account[]>([])
const allAccounts = ref<Account[]>([])
const transactions = ref<Transaction[]>([])
const refreshing = ref(false)
const submitting = ref(false)

const accountNameMap = computed(() => {
  const map: Record<string, string> = {}
  for (const a of allAccounts.value) map[a.id] = a.name
  return map
})

const holdingDialogVisible = ref(false)
const editingHoldingId = ref<string | null>(null)
const txDialogVisible = ref(false)
const txListDialogVisible = ref(false)
const selectedHolding = ref<Holding | null>(null)
const txListHolding = ref<Holding | null>(null)

const holdingForm = reactive({
  account_id: '',
  symbol: '',
  name: '',
  asset_type: 'stock',
  exchange: null as string | null,
  currency: 'CNY',
  quantity: 0,
  include_in_total: true,
  initial_buy_price: 0,
  initial_buy_date: '',
  initial_buy_fee: 0,
  multiplier: null as number | null,
  margin_deposit: null as number | null,
  group_name: null as string | null,
})

const txForm = reactive({
  holding_id: '',
  type: 'buy' as string,
  date: new Date().toISOString().slice(0, 10),
  price: 0,
  quantity: 0,
  fee: 0,
  notes: '',
})

async function fetchHoldings() {
  const { data } = await api.get('/holdings')
  holdings.value = data
}

async function fetchAccounts() {
  const { data } = await api.get('/accounts')
  allAccounts.value = data
  brokerAccounts.value = data
}

async function refreshQuotes() {
  refreshing.value = true
  try {
    await api.post('/market/refresh')
    ElMessage.success('行情已刷新')
    await fetchHoldings()
  } finally {
    refreshing.value = false
  }
}

function autoCurrency(exchange: string | null) {
  if (exchange === 'NYSE' || exchange === 'NASDAQ') return 'USD'
  if (exchange === 'HKSE') return 'HKD'
  return 'CNY'
}

function showHoldingDialog(holding?: Holding) {
  if (holding) {
    editingHoldingId.value = holding.id
    Object.assign(holdingForm, {
      account_id: holding.account_id,
      symbol: holding.symbol,
      name: holding.name,
      asset_type: holding.asset_type,
      exchange: holding.exchange || null,
      currency: holding.currency,
      quantity: holding.quantity,
      include_in_total: holding.include_in_total,
      initial_buy_price: holding.cost_price,
      initial_buy_date: '',
      initial_buy_fee: 0,
      multiplier: holding.multiplier || null,
      margin_deposit: holding.margin_deposit || null,
    })
  } else {
    editingHoldingId.value = null
    Object.assign(holdingForm, {
      account_id: brokerAccounts.value[0]?.id || '',
      symbol: '',
      name: '',
      asset_type: 'stock',
      exchange: null,
      currency: 'CNY',
      quantity: 0,
      include_in_total: true,
      initial_buy_price: 0,
      initial_buy_date: new Date().toISOString().slice(0, 10),
      initial_buy_fee: 0,
      multiplier: null,
      margin_deposit: null,
    })
  }
  holdingDialogVisible.value = true
}

async function handleSaveHolding() {
  submitting.value = true
  try {
    if (editingHoldingId.value) {
      await api.put(`/holdings/${editingHoldingId.value}`, {
        account_id: holdingForm.account_id,
        name: holdingForm.name,
        asset_type: holdingForm.asset_type,
        exchange: holdingForm.exchange,
        currency: holdingForm.currency,
        include_in_total: holdingForm.include_in_total,
        multiplier: holdingForm.multiplier,
        margin_deposit: holdingForm.margin_deposit,
        group_name: holdingForm.group_name,
      })
      ElMessage.success('更新成功')
    } else {
      await api.post('/holdings', {
        ...holdingForm,
        initial_buy_price: holdingForm.initial_buy_price || null,
        initial_buy_date: holdingForm.initial_buy_date || null,
      })
      ElMessage.success('添加成功')
    }
    holdingDialogVisible.value = false
    await fetchHoldings()
  } finally {
    submitting.value = false
  }
}

function showTransactionDialog(holding: Holding) {
  selectedHolding.value = holding
  Object.assign(txForm, {
    holding_id: holding.id,
    type: 'buy',
    date: new Date().toISOString().slice(0, 10),
    price: 0,
    quantity: 0,
    fee: 0,
    notes: '',
  })
  txDialogVisible.value = true
}

async function handleCreateTx() {
  submitting.value = true
  try {
    await api.post('/transactions', txForm)
    ElMessage.success('交易已记录')
    txDialogVisible.value = false
    await fetchHoldings()
  } finally {
    submitting.value = false
  }
}

async function viewTransactions(holding: Holding) {
  txListHolding.value = holding
  const { data } = await api.get('/transactions', { params: { holding_id: holding.id } })
  transactions.value = data
  txListDialogVisible.value = true
}

async function handleDeleteTx(id: string) {
  await api.delete(`/transactions/${id}`)
  ElMessage.success('交易已删除')
  if (txListHolding.value) {
    const { data } = await api.get('/transactions', { params: { holding_id: txListHolding.value.id } })
    transactions.value = data
  }
  await fetchHoldings()
}

async function handleDelete(id: string) {
  await api.delete(`/holdings/${id}`)
  ElMessage.success('删除成功')
  await fetchHoldings()
}

onMounted(async () => {
  await fetchAccounts()
  await fetchHoldings()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 { font-size: 18px; color: #303133; }
.header-actions { display: flex; gap: 8px; }

.text-red { color: #f56c6c; }
.text-green { color: #67c23a; }

.table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

/* 手机端卡片列表默认隐藏 */
.mobile-cards { display: none; }
.desktop-table { display: block; }

/* 手机端持仓卡片 */
.holding-card {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.card-symbol {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

.card-name {
  font-size: 13px;
  color: #606266;
}

.card-type {
  margin-left: 2px;
}

.card-acc {
  font-size: 11px;
  color: #909399;
}

.card-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.card-numbers {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.card-num {
  display: flex;
  flex-direction: column;
}

.num-label {
  font-size: 11px;
  color: #909399;
  margin-bottom: 2px;
}

.num-value {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  word-break: break-all;
}

/* ===== 手机端 <=768px ===== */
@media (max-width: 768px) {
  .mobile-cards { display: block; }
  .desktop-table { display: none; }

  .page-header h2 { font-size: 16px; }

  .card-numbers {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
