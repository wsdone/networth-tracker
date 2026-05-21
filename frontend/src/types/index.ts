export interface Account {
  id: string
  name: string
  type: 'bank' | 'alipay' | 'wechat' | 'broker' | 'overseas_bank' | 'cash' | 'housing_fund'
  institution: string | null
  currency: string
  balance: number
  include_in_total: boolean
  group_name: string | null
  tags: string[] | null
  notes: string | null
  is_active: boolean
  sort_order: number
  margin_enabled: boolean
  own_capital: number
  margin_debt: number | null
  monthly_deposit: number | null
  monthly_offset_amount: number | null
  monthly_offset_day: number | null
  offset_target_account_id: string | null
  created_at: string
  updated_at: string
}

export interface Holding {
  id: string
  account_id: string
  symbol: string
  name: string
  asset_type: 'stock' | 'fund' | 'bond' | 'etf' | 'money_fund' | 'futures'
  exchange: 'SSE' | 'SZSE' | 'HKSE' | 'NYSE' | 'NASDAQ' | 'OTC' | 'SHFE' | 'DCE' | 'CZCE' | 'CFFEX' | 'INE' | 'GFEX' | null
  quantity: number
  cost_price: number
  currency: string
  include_in_total: boolean
  group_name: string | null
  tags: string[] | null
  notes: string | null
  margin_liability_id: string | null
  margin_amount: number | null
  margin_interest_rate: number | null
  multiplier: number | null
  margin_deposit: number | null
  created_at: string
  updated_at: string
  market_price: number | null
  market_value: number | null
  pnl: number | null
  pnl_pct: number | null
}

export interface Transaction {
  id: string
  holding_id: string
  type: 'buy' | 'sell'
  date: string
  price: number
  quantity: number
  amount: number
  fee: number
  notes: string | null
  created_at: string
}

export interface Liability {
  id: string
  type: 'mortgage' | 'personal_loan' | 'credit_card' | 'other_loan'
  name: string
  counterparty: string | null
  balance: number
  currency: string
  interest_rate: number | null
  monthly_payment: number | null
  direction: 'owe' | 'lent'
  include_in_total: boolean
  start_date: string | null
  end_date: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface Overview {
  total_assets_cny: number
  total_liabilities_cny: number
  net_worth_cny: number
  daily_pnl_cny: number
  total_assets_by_currency: Record<string, number>
  total_liabilities_by_currency: Record<string, number>
}

export interface MarketQuote {
  symbol: string
  name: string | null
  price: number
  prev_close: number | null
  change: number | null
  change_pct: number | null
  currency: string
  updated_at: string | null
}

export interface Snapshot {
  id: string
  date: string
  total_assets_cny: number
  total_liabilities_cny: number
  net_worth_cny: number
  daily_pnl_cny: number
  breakdown: Record<string, any> | null
  created_at: string
}

export interface TrendPoint {
  date: string
  total_assets_cny: number
  total_liabilities_cny: number
  net_worth_cny: number
  daily_pnl_cny: number
}

export interface AssetDistributionItem {
  name: string
  value_cny: number
  percentage: number
}

export interface CurrencyOverviewItem {
  currency: string
  currency_name: string
  assets: number
  assets_cny: number
  rate: number | null
}

export interface RepaymentPlan {
  id: string
  liability_id: string
  source_account_id: string
  deduction_day: number
  repayment_type: string
  monthly_rate: number
  monthly_payment: number | null
  monthly_principal: number | null
  is_active: boolean
  liability_name: string | null
  source_account_name: string | null
  next_payment: RepaymentItem | null
  created_at: string
  updated_at: string
}

export interface RepaymentItem {
  id: string
  plan_id: string
  date: string
  principal: number
  interest: number
  total: number
  status: string
  created_at: string
}

export interface RepaymentPlanDetail {
  plan: RepaymentPlan
  items: RepaymentItem[]
  projected_months: number
  total_interest: number
}
