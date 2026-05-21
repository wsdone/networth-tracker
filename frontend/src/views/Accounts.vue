<template>
  <div class="accounts-page">
    <div class="page-header">
      <h2>账户管理</h2>
      <el-button type="primary" :icon="Plus" @click="showDialog()" size="small">添加账户</el-button>
    </div>

    <!-- 桌面端表格 -->
    <el-card shadow="hover" class="desktop-table">
      <div class="table-scroll">
        <el-table :data="accounts" stripe>
          <el-table-column prop="name" label="账户名称" min-width="130" />
          <el-table-column label="类型" width="100">
            <template #default="{ row }"><el-tag size="small">{{ typeLabels[row.type] }}</el-tag></template>
          </el-table-column>
          <el-table-column label="币种" width="80">
            <template #default="{ row }">{{ currencyLabels[row.currency] || row.currency }}</template>
          </el-table-column>
          <el-table-column label="余额" align="right" width="130">
            <template #default="{ row }">
              {{ formatMoney(row.balance, row.currency) }}
              <el-tag v-if="row.margin_enabled && row.margin_debt" size="small" type="warning" style="margin-left:4px">融资 {{ formatMoney(row.margin_debt, row.currency) }}</el-tag>
              <el-tag v-if="row.monthly_deposit" size="small" type="success" style="margin-left:4px">月入 {{ formatMoney(row.monthly_deposit) }}</el-tag>
              <el-tag v-if="row.monthly_offset_amount" size="small" type="warning" style="margin-left:4px">月冲 {{ formatMoney(row.monthly_offset_amount) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="group_name" label="分组" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.group_name" type="info" size="small">{{ row.group_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="showDialog(row)">编辑</el-button>
              <el-button link type="success" @click="showAdjustDialog(row)">调余额</el-button>
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
      <div class="account-card" v-for="acc in accounts" :key="acc.id">
        <div class="card-top">
          <div class="card-info">
            <span class="card-name">{{ acc.name }}</span>
            <el-tag size="small">{{ typeLabels[acc.type] }}</el-tag>
            <el-tag v-if="acc.group_name" type="info" size="small">{{ acc.group_name }}</el-tag>
          </div>
          <div class="card-actions">
            <el-button link type="primary" size="small" @click="showDialog(acc)">编辑</el-button>
            <el-button link type="success" size="small" @click="showAdjustDialog(acc)">调余额</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(acc.id)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
        <div class="card-bottom">
          <span class="card-balance">{{ formatMoney(acc.balance, acc.currency) }}</span>
          <span class="card-currency">{{ currencyLabels[acc.currency] || acc.currency }}</span>
          <template v-if="acc.margin_enabled">
            <el-tag size="small" type="warning" class="card-margin-tag">融资</el-tag>
            <span v-if="acc.margin_debt" class="card-margin-debt">融资负债 {{ formatMoney(acc.margin_debt, acc.currency) }}</span>
          </template>
        </div>
      </div>
      <el-empty v-if="!accounts.length" description="暂无账户" />
    </div>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑账户' : '添加账户'" width="500px" class="responsive-dialog">
      <el-form :model="form" label-width="90px" label-position="top" class="mobile-form">
        <el-form-item label="账户名称" required>
          <el-input v-model="form.name" placeholder="如：招商银行储蓄卡" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="类型" required>
              <el-select v-model="form.type" style="width: 100%">
                <el-option v-for="(label, key) in typeLabels" :key="key" :label="label" :value="key" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="币种">
              <el-select v-model="form.currency" style="width: 100%">
                <el-option label="人民币" value="CNY" />
                <el-option label="港币" value="HKD" />
                <el-option label="美元" value="USD" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="机构">
          <el-input v-model="form.institution" placeholder="如：招商银行" />
        </el-form-item>
        <el-form-item label="余额">
          <el-input-number v-model="form.balance" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="分组">
          <el-input v-model="form.group_name" placeholder="如：应急资金、投资账户" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple filterable allow-create style="width: 100%" placeholder="输入后回车添加标签" />
        </el-form-item>
        <el-form-item label="计入总资产">
          <el-switch v-model="form.include_in_total" />
        </el-form-item>
        <el-divider v-if="form.type === 'broker'">融资融券</el-divider>
        <template v-if="form.type === 'broker'">
          <el-form-item label="融资账户">
            <el-switch v-model="form.margin_enabled" />
          </el-form-item>
          <template v-if="form.margin_enabled">
            <el-form-item label="自有资金">
              <el-input-number v-model="form.own_capital" :precision="2" :min="0" style="width: 100%" />
            </el-form-item>
            <div class="margin-tip" v-if="form.own_capital > 0">
              例如自有 {{ formatMoney(form.own_capital) }}，2倍杠杆最多可持有 {{ formatMoney(form.own_capital * 2) }} 仓位
            </div>
          </template>
        </template>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
        <template v-if="form.type === 'housing_fund'">
          <el-divider>公积金设置</el-divider>
          <el-form-item label="每月到账金额">
            <el-input-number v-model="form.monthly_deposit" :precision="2" :min="0" style="width: 100%" placeholder="单位和个人缴存合计" />
          </el-form-item>
          <el-divider>月冲设置（可选）</el-divider>
          <el-form-item label="月冲金额">
            <el-input-number v-model="form.monthly_offset_amount" :precision="2" :min="0" style="width: 100%" placeholder="每月自动扣除的金额" />
          </el-form-item>
          <el-form-item label="月冲日期">
            <el-input-number v-model="form.monthly_offset_day" :min="1" :max="28" style="width: 100%" placeholder="每月几号执行月冲" />
          </el-form-item>
          <el-form-item label="月冲目标账户">
            <el-select v-model="form.offset_target_account_id" clearable style="width: 100%" placeholder="月冲打到哪张银行卡">
              <el-option v-for="acc in accounts.filter(a => a.type === 'bank' && a.id !== editingId)" :key="acc.id" :label="acc.name" :value="acc.id" />
            </el-select>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 调整余额对话框 -->
    <el-dialog v-model="adjustDialogVisible" title="调整余额" width="380px" class="responsive-dialog">
      <div style="margin-bottom: 12px; font-size: 14px; color: #606266">
        <strong>{{ adjustAccount?.name }}</strong> 当前余额：<span style="font-weight:600">{{ formatMoney(adjustAccount?.balance || 0, adjustAccount?.currency) }}</span>
      </div>
      <el-input-number v-model="adjustBalance" :precision="2" style="width: 100%" placeholder="输入新余额" />
      <div style="margin-top: 8px; font-size: 12px; color: #909399">直接设置为新余额，差值 = 新余额 - 当前余额</div>
      <template #footer>
        <el-button @click="adjustDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdjust" :loading="adjustSubmitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { formatMoney } from '@/utils/format'
import type { Account } from '@/types'

const typeLabels: Record<string, string> = {
  bank: '银行卡', alipay: '支付宝', wechat: '微信',
  broker: '券商', overseas_bank: '境外银行', cash: '现金',
  housing_fund: '公积金',
}
const currencyLabels: Record<string, string> = { CNY: '人民币', HKD: '港币', USD: '美元' }

const accounts = ref<Account[]>([])
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const submitting = ref(false)
const adjustDialogVisible = ref(false)
const adjustAccount = ref<Account | null>(null)
const adjustBalance = ref(0)
const adjustSubmitting = ref(false)

const defaultForm = {
  name: '', type: 'bank' as string, institution: '', currency: 'CNY',
  balance: 0, include_in_total: true, group_name: '', tags: [] as string[], notes: '',
  margin_enabled: false, own_capital: 0,
  monthly_deposit: null as number | null, monthly_offset_amount: null as number | null,
  monthly_offset_day: null as number | null, offset_target_account_id: null as string | null,
}
const form = reactive({ ...defaultForm })

async function fetchAccounts() {
  const { data } = await api.get('/accounts')
  accounts.value = data
}

function showDialog(account?: Account) {
  if (account) {
    editingId.value = account.id
    Object.assign(form, {
      name: account.name, type: account.type, institution: account.institution || '',
      currency: account.currency, balance: account.balance, include_in_total: account.include_in_total,
      group_name: account.group_name || '', tags: account.tags || [], notes: account.notes || '',
      margin_enabled: account.margin_enabled || false, own_capital: account.own_capital || 0,
      monthly_deposit: account.monthly_deposit || null,
      monthly_offset_amount: account.monthly_offset_amount || null,
      monthly_offset_day: account.monthly_offset_day || null,
      offset_target_account_id: account.offset_target_account_id || null,
    })
  } else {
    editingId.value = null
    Object.assign(form, defaultForm)
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  submitting.value = true
  try {
    const payload = { ...form, institution: form.institution || null, group_name: form.group_name || null, notes: form.notes || null }
    if (editingId.value) {
      await api.put(`/accounts/${editingId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/accounts', payload)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    await fetchAccounts()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: string) {
  await api.delete(`/accounts/${id}`)
  ElMessage.success('删除成功')
  await fetchAccounts()
}

function showAdjustDialog(acc: Account) {
  adjustAccount.value = acc
  adjustBalance.value = acc.balance
  adjustDialogVisible.value = true
}

async function handleAdjust() {
  if (!adjustAccount.value) return
  adjustSubmitting.value = true
  try {
    await api.put(`/accounts/${adjustAccount.value.id}`, { balance: adjustBalance.value })
    ElMessage.success('余额已更新')
    adjustDialogVisible.value = false
    await fetchAccounts()
  } finally {
    adjustSubmitting.value = false
  }
}

onMounted(fetchAccounts)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 { font-size: 18px; color: #303133; }

.table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.mobile-cards { display: none; }
.desktop-table { display: block; }

.account-card {
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
  margin-bottom: 8px;
}

.card-info {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.card-name {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

.card-actions { display: flex; gap: 2px; flex-shrink: 0; }

.card-bottom {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.card-balance {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.card-currency {
  font-size: 12px;
  color: #909399;
}

.card-margin-tag { margin-left: 4px; }
.card-margin-debt { font-size: 12px; color: #e6a23c; }

.margin-tip {
  font-size: 12px;
  color: #909399;
  margin-top: -8px;
  margin-bottom: 12px;
}

@media (max-width: 768px) {
  .mobile-cards { display: block; }
  .desktop-table { display: none; }
  .page-header h2 { font-size: 16px; }
}
</style>
