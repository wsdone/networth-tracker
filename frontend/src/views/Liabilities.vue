<template>
  <div class="liabilities-page">
    <div class="page-header">
      <h2>负债管理</h2>
      <el-button type="primary" :icon="Plus" @click="showDialog()" size="small">添加负债</el-button>
    </div>

    <!-- 我欠别人 -->
    <el-card shadow="hover" class="section-card">
      <template #header>
        <div class="section-header">
          <span class="section-title text-red">我欠别人</span>
          <span class="section-total">{{ formatMoney(oweTotal) }}</span>
        </div>
      </template>
      <!-- 桌面 -->
      <div class="table-scroll desktop-table">
        <el-table :data="oweList" stripe>
          <el-table-column prop="name" label="名称" min-width="120" />
          <el-table-column label="类型" width="100">
            <template #default="{ row }"><el-tag size="small">{{ typeLabels[row.type] }}</el-tag></template>
          </el-table-column>
          <el-table-column label="余额" align="right" width="130">
            <template #default="{ row }">{{ formatMoney(row.balance, row.currency) }}</template>
          </el-table-column>
          <el-table-column label="利率" align="right" width="70">
            <template #default="{ row }">{{ row.interest_rate ? row.interest_rate + '%' : '--' }}</template>
          </el-table-column>
          <el-table-column label="月供" align="right" width="110">
            <template #default="{ row }">{{ row.monthly_payment ? formatMoney(row.monthly_payment, row.currency) : '--' }}</template>
          </el-table-column>
          <el-table-column label="还款计划" width="90" align="center">
            <template #default="{ row }">
              <el-tag v-if="getPlanForLiability(row.id)" size="small" type="success">已设</el-tag>
              <span v-else>--</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{ row }">
              <el-button link type="success" @click="showRepayDialog(row)">还款</el-button>
              <el-button link type="primary" @click="showDialog(row)">编辑</el-button>
              <el-button v-if="!getPlanForLiability(row.id)" link type="warning" @click="showPlanDialog(row)">还款计划</el-button>
              <el-button v-else link type="success" @click="viewPlan(row)">查看计划</el-button>
              <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
                <template #reference>
                  <el-button link type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <!-- 手机 -->
      <div class="mobile-cards">
        <div class="liab-card" v-for="item in oweList" :key="item.id">
          <div class="card-top">
            <div class="card-info">
              <span class="card-name">{{ item.name }}</span>
              <el-tag size="small">{{ typeLabels[item.type] }}</el-tag>
              <el-tag v-if="getPlanForLiability(item.id)" size="small" type="success">还款计划</el-tag>
            </div>
            <div class="card-actions">
              <el-button link type="success" size="small" @click="showRepayDialog(item)">还款</el-button>
              <el-button link type="primary" size="small" @click="showDialog(item)">编辑</el-button>
              <el-button v-if="!getPlanForLiability(item.id)" link type="warning" size="small" @click="showPlanDialog(item)">还款计划</el-button>
              <el-button v-else link type="success" size="small" @click="viewPlan(item)">查看</el-button>
              <el-popconfirm title="确定删除？" @confirm="handleDelete(item.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
          <div class="card-bottom">
            <span class="card-amount text-red">{{ formatMoney(item.balance, item.currency) }}</span>
            <span v-if="item.monthly_payment" class="card-meta">月供 {{ formatMoney(item.monthly_payment, item.currency) }}</span>
          </div>
        </div>
        <el-empty v-if="!oweList.length" description="暂无" :image-size="60" />
      </div>
    </el-card>

    <!-- 别人欠我 -->
    <el-card shadow="hover" class="section-card">
      <template #header>
        <div class="section-header">
          <span class="section-title text-green">别人欠我</span>
          <span class="section-total">{{ formatMoney(lentTotal) }}</span>
        </div>
      </template>
      <div class="table-scroll desktop-table">
        <el-table :data="lentList" stripe>
          <el-table-column prop="name" label="名称" min-width="120" />
          <el-table-column label="类型" width="100">
            <template #default="{ row }"><el-tag size="small">{{ typeLabels[row.type] }}</el-tag></template>
          </el-table-column>
          <el-table-column label="余额" align="right" width="130">
            <template #default="{ row }">{{ formatMoney(row.balance, row.currency) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="success" @click="showCollectDialog(row)">收回</el-button>
              <el-button link type="primary" @click="showDialog(row)">编辑</el-button>
              <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
                <template #reference>
                  <el-button link type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="mobile-cards">
        <div class="liab-card" v-for="item in lentList" :key="item.id">
          <div class="card-top">
            <div class="card-info">
              <span class="card-name">{{ item.name }}</span>
              <el-tag size="small">{{ typeLabels[item.type] }}</el-tag>
            </div>
            <div class="card-actions">
              <el-button link type="success" size="small" @click="showCollectDialog(item)">收回</el-button>
              <el-button link type="primary" size="small" @click="showDialog(item)">编辑</el-button>
              <el-popconfirm title="确定删除？" @confirm="handleDelete(item.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
          <div class="card-bottom">
            <span class="card-amount text-green">{{ formatMoney(item.balance, item.currency) }}</span>
          </div>
        </div>
        <el-empty v-if="!lentList.length" description="暂无" :image-size="60" />
      </div>
    </el-card>

    <!-- 添加/编辑负债对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑负债' : '添加负债'" width="500px" class="responsive-dialog">
      <el-form :model="form" label-width="80px" label-position="top" class="mobile-form">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="名称" required>
              <el-input v-model="form.name" placeholder="如：房贷" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="类型" required>
              <el-select v-model="form.type" style="width: 100%">
                <el-option v-for="(label, key) in typeLabels" :key="key" :label="label" :value="key" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="方向" required>
              <el-radio-group v-model="form.direction">
                <el-radio value="owe">我欠别人</el-radio>
                <el-radio value="lent">别人欠我</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="对方">
              <el-input v-model="form.counterparty" placeholder="如：银行" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="余额" required>
              <el-input-number v-model="form.balance" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="币种">
              <el-select v-model="form.currency" style="width: 100%">
                <el-option label="人民币" value="CNY" />
                <el-option label="港币" value="HKD" />
                <el-option label="美元" value="USD" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="年利率%">
              <el-input-number v-model="form.interest_rate" :precision="2" :min="0" :max="100" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="月供">
              <el-input-number v-model="form.monthly_payment" :precision="2" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计入总负债">
              <el-switch v-model="form.include_in_total" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="起始日期">
              <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束日期">
              <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 还款计划设置对话框 -->
    <el-dialog v-model="planDialogVisible" title="设置还款计划" width="600px" class="responsive-dialog">
      <div class="plan-intro">
        <p>请填写接下来 <b>2-3 个月</b>的还款明细，系统将自动推算完整还款计划。</p>
        <p class="plan-hint">每期还款 = 本金部分 + 利息部分，利息部分逐月递减</p>
      </div>

      <el-form :model="planForm" label-position="top" class="mobile-form">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="扣款账户">
              <el-select v-model="planForm.source_account_id" style="width: 100%">
                <el-option v-for="acc in accounts" :key="acc.id" :label="acc.name" :value="acc.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="每月扣款日">
              <el-select v-model="planForm.deduction_day" style="width: 100%">
                <el-option v-for="d in 28" :key="d" :label="`每月${d}日`" :value="d" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="年利率%（可选，不填则从明细推算）">
          <el-input-number v-model="planForm.annual_interest_rate" :precision="2" :min="0" :max="100" style="width: 200px" placeholder="如 3.3" />
        </el-form-item>

        <el-divider>还款明细校准</el-divider>
        <div class="entry-table">
          <div class="entry-row entry-header">
            <span>月份</span>
            <span>本金</span>
            <span>利息</span>
            <span>合计</span>
          </div>
          <div class="entry-row" v-for="(entry, idx) in planForm.entries" :key="idx">
            <el-date-picker v-model="entry.month" type="month" value-format="YYYY-MM" placeholder="选择月份" style="width: 110px" />
            <el-input-number v-model="entry.principal" :precision="2" :min="0" style="width: 120px" placeholder="本金" />
            <el-input-number v-model="entry.interest" :precision="2" :min="0" style="width: 120px" placeholder="利息" />
            <span class="entry-total">{{ formatMoney((entry.principal || 0) + (entry.interest || 0)) }}</span>
            <el-button v-if="planForm.entries.length > 2" link type="danger" @click="planForm.entries.splice(idx, 1)">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>
        <el-button link type="primary" @click="planForm.entries.push({ month: '', principal: 0, interest: 0 })">+ 添加一行</el-button>
      </el-form>

      <template #footer>
        <el-button @click="planDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreatePlan" :loading="submitting">创建还款计划</el-button>
      </template>
    </el-dialog>

    <!-- 编辑还款计划对话框 -->
    <el-dialog v-model="editPlanDialogVisible" title="编辑还款计划" width="600px" class="responsive-dialog">
      <p class="plan-intro">修改参数后，系统将从<b>当前贷款余额</b>重新推算剩余还款计划。已执行的还款不受影响。</p>

      <el-form :model="editPlanForm" label-position="top" class="mobile-form">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="扣款账户">
              <el-select v-model="editPlanForm.source_account_id" style="width: 100%">
                <el-option v-for="acc in accounts" :key="acc.id" :label="acc.name" :value="acc.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="每月扣款日">
              <el-select v-model="editPlanForm.deduction_day" style="width: 100%">
                <el-option v-for="d in 28" :key="d" :label="`每月${d}日`" :value="d" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="年利率%">
          <el-input-number v-model="editPlanForm.annual_interest_rate" :precision="2" :min="0" :max="100" style="width: 200px" />
          <span class="rate-hint">修改利率会重新推算剩余期数</span>
        </el-form-item>

        <el-divider>重新校准（可选，填写后覆盖利率推算）</el-divider>
        <p class="plan-hint">填写接下来2个月的还款明细来校准，留空则只用利率推算</p>
        <div class="entry-table">
          <div class="entry-row entry-header">
            <span>月份</span>
            <span>本金</span>
            <span>利息</span>
            <span>合计</span>
          </div>
          <div class="entry-row" v-for="(entry, idx) in editPlanForm.entries" :key="idx">
            <el-date-picker v-model="entry.month" type="month" value-format="YYYY-MM" placeholder="选择月份" style="width: 110px" />
            <el-input-number v-model="entry.principal" :precision="2" :min="0" style="width: 120px" />
            <el-input-number v-model="entry.interest" :precision="2" :min="0" style="width: 120px" />
            <span class="entry-total">{{ formatMoney((entry.principal || 0) + (entry.interest || 0)) }}</span>
          </div>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="editPlanDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpdatePlan" :loading="submitting">保存并重新推算</el-button>
      </template>
    </el-dialog>

    <!-- 查看还款计划对话框 -->
    <el-dialog v-model="planDetailVisible" title="还款计划详情" width="700px" class="responsive-dialog">
      <template v-if="planDetail">
        <div class="plan-summary">
          <div class="plan-stat">
            <span class="plan-label">还款方式</span>
            <span>{{ repaymentTypeLabel }}</span>
          </div>
          <div class="plan-stat">
            <span class="plan-label">月利率</span>
            <span>{{ (planDetail.plan.monthly_rate * 100).toFixed(4) }}%</span>
          </div>
          <div class="plan-stat">
            <span class="plan-label">剩余期数</span>
            <span>{{ planDetail.projected_months }} 期</span>
          </div>
          <div class="plan-stat">
            <span class="plan-label">预计总利息</span>
            <span class="text-red">{{ formatMoney(planDetail.total_interest) }}</span>
          </div>
          <div class="plan-stat" v-if="planDetail.plan.next_payment">
            <span class="plan-label">下期扣款</span>
            <span>{{ planDetail.plan.next_payment.date }} / {{ formatMoney(planDetail.plan.next_payment.total) }}</span>
          </div>
        </div>

        <div class="plan-actions">
          <el-button type="primary" size="small" @click="executePayment" :loading="executing">手动执行扣款</el-button>
          <el-button type="warning" size="small" @click="showEditPlanDialog">编辑计划</el-button>
          <el-popconfirm title="确定删除还款计划？" @confirm="handleDeletePlan">
            <template #reference>
              <el-button type="danger" size="small">删除计划</el-button>
            </template>
          </el-popconfirm>
        </div>

        <div class="table-scroll">
          <el-table :data="planDetail.items" stripe max-height="400" size="small">
            <el-table-column prop="date" label="日期" width="100" />
            <el-table-column label="本金" align="right" width="110">
              <template #default="{ row }">{{ formatMoney(row.principal) }}</template>
            </el-table-column>
            <el-table-column label="利息" align="right" width="110">
              <template #default="{ row }">{{ formatMoney(row.interest) }}</template>
            </el-table-column>
            <el-table-column label="合计" align="right" width="110">
              <template #default="{ row }">{{ formatMoney(row.total) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="70" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'paid' ? 'success' : 'info'" size="small">{{ row.status === 'paid' ? '已扣' : '待扣' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </el-dialog>

    <!-- 手动还款对话框 -->
    <el-dialog v-model="repayDialogVisible" :title="`还款 - ${repayLiability?.name || ''}`" width="420px" class="responsive-dialog">
      <div style="margin-bottom: 12px; font-size: 13px; color: #909399">
        当前欠款：<span class="text-red">{{ formatMoney(repayLiability?.balance || 0, repayLiability?.currency) }}</span>
      </div>
      <el-form :model="repayForm" label-width="80px" label-position="top" class="mobile-form">
        <el-form-item label="还款账户" required>
          <el-select v-model="repayForm.account_id" style="width: 100%">
            <el-option v-for="acc in accounts" :key="acc.id" :label="`${acc.name} (${formatMoney(acc.balance, acc.currency)})`" :value="acc.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="本金" required>
              <el-input-number v-model="repayForm.principal" :precision="2" :min="0" :max="repayLiability?.balance || 0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="利息">
              <el-input-number v-model="repayForm.interest" :precision="2" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <div class="repay-summary">
          <span>合计扣款：<b>{{ formatMoney(repayForm.principal + repayForm.interest) }}</b></span>
          <span style="margin-left: 16px">剩余欠款：<b class="text-red">{{ formatMoney((repayLiability?.balance || 0) - repayForm.principal) }}</b></span>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="repayDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRepay" :loading="repaySubmitting" :disabled="!repayForm.account_id || repayForm.principal <= 0">确认还款</el-button>
      </template>
    </el-dialog>

    <!-- 收回欠款对话框 -->
    <el-dialog v-model="collectDialogVisible" :title="`收回 - ${collectLiability?.name || ''}`" width="420px" class="responsive-dialog">
      <div style="margin-bottom: 12px; font-size: 13px; color: #909399">
        待收回金额：<span class="text-green">{{ formatMoney(collectLiability?.balance || 0, collectLiability?.currency) }}</span>
      </div>
      <el-form :model="collectForm" label-width="80px" label-position="top" class="mobile-form">
        <el-form-item label="收款账户" required>
          <el-select v-model="collectForm.account_id" style="width: 100%">
            <el-option v-for="acc in accounts" :key="acc.id" :label="`${acc.name} (${formatMoney(acc.balance, acc.currency)})`" :value="acc.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="收回金额" required>
          <el-input-number v-model="collectForm.amount" :precision="2" :min="0" :max="collectLiability?.balance || 0" style="width: 100%" />
        </el-form-item>
        <div class="repay-summary">
          <span>收回后余额：<b class="text-green">{{ formatMoney((collectLiability?.balance || 0) - collectForm.amount) }}</b></span>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="collectDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCollect" :loading="collectSubmitting" :disabled="!collectForm.account_id || collectForm.amount <= 0">确认收回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { Plus, Close } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { formatMoney } from '@/utils/format'
import type { Liability, Account, RepaymentPlan, RepaymentPlanDetail } from '@/types'

const typeLabels: Record<string, string> = {
  mortgage: '房贷', personal_loan: '个人借款', credit_card: '信用卡/花呗', other_loan: '其他贷款',
}

const liabilities = ref<Liability[]>([])
const accounts = ref<Account[]>([])
const plans = ref<RepaymentPlan[]>([])
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const submitting = ref(false)

// Repayment plan state
const planDialogVisible = ref(false)
const planDetailVisible = ref(false)
const editPlanDialogVisible = ref(false)
const planDetail = ref<RepaymentPlanDetail | null>(null)
const selectedLiability = ref<Liability | null>(null)
const executing = ref(false)

// Repay state
const repayDialogVisible = ref(false)
const repayLiability = ref<Liability | null>(null)
const repaySubmitting = ref(false)
const repayForm = reactive({ account_id: '', principal: 0, interest: 0 })

// Collect state (别人欠我 收回)
const collectDialogVisible = ref(false)
const collectLiability = ref<Liability | null>(null)
const collectSubmitting = ref(false)
const collectForm = reactive({ account_id: '', amount: 0 })

const editPlanForm = reactive({
  source_account_id: '',
  deduction_day: 15,
  annual_interest_rate: 0 as number | null,
  entries: [
    { month: '', principal: 0, interest: 0 },
    { month: '', principal: 0, interest: 0 },
  ],
})

const planForm = reactive({
  source_account_id: '',
  deduction_day: 15,
  annual_interest_rate: null as number | null,
  entries: [
    { month: '', principal: 0, interest: 0 },
    { month: '', principal: 0, interest: 0 },
  ],
})

const oweList = computed(() => liabilities.value.filter(l => l.direction === 'owe'))
const lentList = computed(() => liabilities.value.filter(l => l.direction === 'lent'))
const oweTotal = computed(() => oweList.value.reduce((s, l) => s + l.balance, 0))
const lentTotal = computed(() => lentList.value.reduce((s, l) => s + l.balance, 0))

const repaymentTypeLabel = computed(() => {
  if (!planDetail.value) return ''
  const t = planDetail.value.plan.repayment_type
  if (t === 'equal_payment') return '等额本息'
  if (t === 'equal_principal') return '等额本金'
  return '自定义'
})

function getPlanForLiability(liabilityId: string): RepaymentPlan | undefined {
  return plans.value.find(p => p.liability_id === liabilityId)
}

async function fetchData() {
  const [liabRes, accRes, planRes] = await Promise.all([
    api.get('/liabilities'),
    api.get('/accounts'),
    api.get('/repayment-plans'),
  ])
  liabilities.value = liabRes.data
  accounts.value = accRes.data
  plans.value = planRes.data
}

// --- Liability CRUD ---
const defaultForm = {
  name: '', type: 'mortgage', direction: 'owe', counterparty: '', balance: 0,
  currency: 'CNY', interest_rate: null as number | null, monthly_payment: null as number | null,
  include_in_total: true, start_date: null as string | null, end_date: null as string | null, notes: '',
}
const form = reactive({ ...defaultForm })

function showDialog(item?: Liability) {
  if (item) {
    editingId.value = item.id
    Object.assign(form, {
      name: item.name, type: item.type, direction: item.direction,
      counterparty: item.counterparty || '', balance: item.balance, currency: item.currency,
      interest_rate: item.interest_rate, monthly_payment: item.monthly_payment,
      include_in_total: item.include_in_total, start_date: item.start_date,
      end_date: item.end_date, notes: item.notes || '',
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
    const payload = { ...form, counterparty: form.counterparty || null, notes: form.notes || null }
    if (editingId.value) {
      await api.put(`/liabilities/${editingId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/liabilities', payload)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: string) {
  await api.delete(`/liabilities/${id}`)
  ElMessage.success('删除成功')
  await fetchData()
}

// --- Repayment Plan ---
function showPlanDialog(item: Liability) {
  selectedLiability.value = item
  // Pre-fill interest rate from liability
  planForm.annual_interest_rate = item.interest_rate
  planForm.source_account_id = accounts.value[0]?.id || ''
  planForm.deduction_day = 15
  // Pre-fill next 2 months
  const now = new Date()
  const m1 = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const nextMonth = now.getMonth() + 2 > 12 ? now.getFullYear() + 1 : now.getFullYear()
  const nextM = now.getMonth() + 2 > 12 ? now.getMonth() + 2 - 12 : now.getMonth() + 2
  const m2 = `${nextMonth}-${String(nextM).padStart(2, '0')}`
  planForm.entries = [
    { month: m1, principal: 0, interest: 0 },
    { month: m2, principal: 0, interest: 0 },
  ]
  planDialogVisible.value = true
}

async function handleCreatePlan() {
  if (!selectedLiability.value) return
  const validEntries = planForm.entries.filter(e => e.month && (e.principal > 0 || e.interest > 0))
  if (validEntries.length < 2) {
    return ElMessage.warning('请至少填写2个月的还款明细')
  }

  submitting.value = true
  try {
    const { data } = await api.post('/repayment-plans', {
      liability_id: selectedLiability.value.id,
      source_account_id: planForm.source_account_id,
      deduction_day: planForm.deduction_day,
      annual_interest_rate: planForm.annual_interest_rate || null,
      entries: validEntries,
    })
    planDialogVisible.value = false
    planDetail.value = data
    planDetailVisible.value = true
    await fetchData()
    ElMessage.success(`还款计划已创建，共 ${data.projected_months} 期，预计总利息 ${formatMoney(data.total_interest)}`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

async function viewPlan(item: Liability) {
  const plan = getPlanForLiability(item.id)
  if (!plan) return
  const { data } = await api.get(`/repayment-plans/${plan.id}`)
  planDetail.value = data
  planDetailVisible.value = true
}

function showEditPlanDialog() {
  if (!planDetail.value) return
  const p = planDetail.value.plan
  editPlanForm.source_account_id = p.source_account_id
  editPlanForm.deduction_day = p.deduction_day
  editPlanForm.annual_interest_rate = parseFloat((p.monthly_rate * 12 * 100).toFixed(4))
  // Pre-fill next 2 months
  const now = new Date()
  const m1 = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const nextMonth = now.getMonth() + 2 > 12 ? now.getFullYear() + 1 : now.getFullYear()
  const nextM = now.getMonth() + 2 > 12 ? now.getMonth() + 2 - 12 : now.getMonth() + 2
  const m2 = `${nextMonth}-${String(nextM).padStart(2, '0')}`
  editPlanForm.entries = [
    { month: m1, principal: 0, interest: 0 },
    { month: m2, principal: 0, interest: 0 },
  ]
  editPlanDialogVisible.value = true
}

async function handleUpdatePlan() {
  if (!planDetail.value) return
  submitting.value = true
  try {
    const payload: any = {
      source_account_id: editPlanForm.source_account_id,
      deduction_day: editPlanForm.deduction_day,
      annual_interest_rate: editPlanForm.annual_interest_rate || null,
    }
    const validEntries = editPlanForm.entries.filter(e => e.month && (e.principal > 0 || e.interest > 0))
    if (validEntries.length >= 2) {
      payload.entries = validEntries
    }
    const { data } = await api.put(`/repayment-plans/${planDetail.value.plan.id}`, payload)
    planDetail.value = data
    editPlanDialogVisible.value = false
    await fetchData()
    ElMessage.success(`计划已更新，剩余 ${data.projected_months} 期，总利息 ${formatMoney(data.total_interest)}`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '更新失败')
  } finally {
    submitting.value = false
  }
}

async function executePayment() {
  if (!planDetail.value) return
  executing.value = true
  try {
    const { data } = await api.post(`/repayment-plans/${planDetail.value.plan.id}/execute`)
    if (data.executed) {
      ElMessage.success(`扣款成功：本金 ${formatMoney(data.principal)}，利息 ${formatMoney(data.interest)}，合计 ${formatMoney(data.total)}`)
      // Refresh plan detail
      const { data: updated } = await api.get(`/repayment-plans/${planDetail.value.plan.id}`)
      planDetail.value = updated
      await fetchData()
    } else {
      ElMessage.info('没有待执行的还款')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '扣款失败')
  } finally {
    executing.value = false
  }
}

// --- Manual Repay ---
function showRepayDialog(item: Liability) {
  repayLiability.value = item
  repayForm.account_id = accounts.value[0]?.id || ''
  repayForm.principal = 0
  repayForm.interest = 0
  repayDialogVisible.value = true
}

async function handleRepay() {
  if (!repayLiability.value || !repayForm.account_id || repayForm.principal <= 0) return
  repaySubmitting.value = true
  try {
    const { data } = await api.post(`/liabilities/${repayLiability.value.id}/repay`, {
      account_id: repayForm.account_id,
      principal: repayForm.principal,
      interest: repayForm.interest,
    })
    ElMessage.success(`还款成功：本金 ${formatMoney(data.principal)}，利息 ${formatMoney(data.interest)}，合计 ${formatMoney(data.total)}`)
    repayDialogVisible.value = false
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '还款失败')
  } finally {
    repaySubmitting.value = false
  }
}

async function handleDeletePlan() {
  if (!planDetail.value) return
  await api.delete(`/repayment-plans/${planDetail.value.plan.id}`)
  ElMessage.success('还款计划已删除')
  planDetailVisible.value = false
  planDetail.value = null
  await fetchData()
}

// --- Collect (别人欠我) ---
function showCollectDialog(item: Liability) {
  collectLiability.value = item
  collectForm.account_id = accounts.value[0]?.id || ''
  collectForm.amount = item.balance
  collectDialogVisible.value = true
}

async function handleCollect() {
  if (!collectLiability.value || !collectForm.account_id || collectForm.amount <= 0) return
  collectSubmitting.value = true
  try {
    const { data } = await api.post(`/liabilities/${collectLiability.value.id}/collect`, {
      account_id: collectForm.account_id,
      amount: collectForm.amount,
    })
    ElMessage.success(`收回成功：${formatMoney(data.amount)}，剩余 ${formatMoney(data.remaining)}`)
    collectDialogVisible.value = false
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '收回失败')
  } finally {
    collectSubmitting.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 { font-size: 18px; color: #303133; }
.section-card { margin-bottom: 16px; }
.section-header { display: flex; justify-content: space-between; align-items: center; }
.section-title { font-weight: 600; }
.section-total { font-size: 14px; color: #909399; }
.text-red { color: #f56c6c; }
.text-green { color: #67c23a; }

.table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.mobile-cards { display: none; }
.desktop-table { display: block; }

.liab-card {
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}
.liab-card:last-child { border-bottom: none; }

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 6px;
}
.card-info { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.card-name { font-weight: 600; font-size: 15px; color: #303133; }
.card-actions { display: flex; gap: 2px; flex-shrink: 0; }
.card-bottom { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.card-amount { font-size: 18px; font-weight: 600; }
.card-meta { font-size: 12px; color: #909399; }

.repay-summary {
  font-size: 13px; color: #606266; padding: 8px 0;
  border-top: 1px solid #ebeef5; margin-top: 4px;
}

/* Plan dialog styles */
.plan-intro {
  font-size: 13px;
  color: #606266;
  margin-bottom: 16px;
  line-height: 1.6;
}
.plan-hint { color: #909399; font-size: 12px; margin-top: 4px; }
.rate-hint { font-size: 12px; color: #909399; margin-left: 12px; }

.entry-table {
  margin-bottom: 8px;
}
.entry-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.entry-header {
  font-size: 12px;
  color: #909399;
  padding-bottom: 4px;
  border-bottom: 1px solid #ebeef5;
}
.entry-header span { flex: 1; text-align: center; }
.entry-header span:first-child { flex: 1.1; }
.entry-total {
  width: 100px;
  text-align: right;
  font-size: 13px;
  color: #303133;
  font-weight: 500;
}

/* Plan detail */
.plan-summary {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.plan-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.plan-label {
  font-size: 11px;
  color: #909399;
}
.plan-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

@media (max-width: 768px) {
  .mobile-cards { display: block; }
  .desktop-table { display: none; }
  .page-header h2 { font-size: 16px; }
  .entry-row { flex-wrap: wrap; }
  .entry-total { width: 80px; }
  .plan-summary { grid-template-columns: repeat(2, 1fr); }
}
</style>
