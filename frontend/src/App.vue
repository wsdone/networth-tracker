<template>
  <div class="app-layout">
    <!-- 移动端顶栏 -->
    <div class="mobile-header">
      <div class="mobile-header-left">
        <el-icon :size="20" @click="mobileMenuOpen = true"><Operation /></el-icon>
        <span class="mobile-logo">资产管理</span>
      </div>
    </div>

    <!-- 遮罩 -->
    <div v-if="mobileMenuOpen" class="mobile-overlay" @click="mobileMenuOpen = false"></div>

    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ 'sidebar-open': mobileMenuOpen }">
      <div class="logo">
        <el-icon :size="24"><Wallet /></el-icon>
        <span>资产管理</span>
        <el-icon class="mobile-close" @click="mobileMenuOpen = false"><Close /></el-icon>
      </div>

      <div class="nav-section">
        <div class="nav-section-title">总览</div>
        <router-link to="/dashboard" class="nav-item" active-class="active" @click="mobileMenuOpen = false">
          <el-icon><DataAnalysis /></el-icon>
          <span>仪表盘</span>
        </router-link>
        <router-link to="/reports" class="nav-item" active-class="active" @click="mobileMenuOpen = false">
          <el-icon><TrendCharts /></el-icon>
          <span>报表中心</span>
        </router-link>
        <router-link to="/expenses" class="nav-item" active-class="active" @click="mobileMenuOpen = false">
          <el-icon><ShoppingCart /></el-icon>
          <span>消费概览</span>
        </router-link>
      </div>

      <div class="nav-section">
        <div class="nav-section-title">管理</div>
        <router-link to="/accounts" class="nav-item" active-class="active" @click="mobileMenuOpen = false">
          <el-icon><CreditCard /></el-icon>
          <span>账户管理</span>
        </router-link>
        <router-link to="/holdings" class="nav-item" active-class="active" @click="mobileMenuOpen = false">
          <el-icon><Histogram /></el-icon>
          <span>持仓管理</span>
        </router-link>
        <router-link to="/liabilities" class="nav-item" active-class="active" @click="mobileMenuOpen = false">
          <el-icon><Document /></el-icon>
          <span>负债管理</span>
        </router-link>
        <router-link to="/settings" class="nav-item" active-class="active" @click="mobileMenuOpen = false">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </router-link>
      </div>
    </aside>

    <!-- 主内容 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Wallet, DataAnalysis, TrendCharts, ShoppingCart, CreditCard, Histogram, Document, Setting, Operation, Close } from '@element-plus/icons-vue'

const mobileMenuOpen = ref(false)
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f5f7fa;
}

.app-layout {
  min-height: 100vh;
  display: flex;
}

/* 侧边栏 */
.sidebar {
  width: 220px;
  min-width: 220px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
  height: 100vh;
  position: sticky;
  top: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 20px 20px 16px;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  border-bottom: 1px solid #f0f0f0;
}

.mobile-close { display: none; }

.nav-section { padding: 16px 0 8px; }

.nav-section-title {
  padding: 0 20px 8px;
  font-size: 12px;
  color: #909399;
  letter-spacing: 1px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  color: #606266;
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}

.nav-item:hover { background: #f5f7fa; color: #409eff; }
.nav-item.active { background: #ecf5ff; color: #409eff; font-weight: 500; }

/* 主内容 */
.main-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  min-width: 0;
}

/* 移动端顶栏 */
.mobile-header { display: none; }
.mobile-overlay { display: none; }

/* ========== 响应式: <=768px ========== */
@media (max-width: 768px) {
  .app-layout { flex-direction: column; }

  .mobile-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    background: #fff;
    border-bottom: 1px solid #e4e7ed;
    position: sticky;
    top: 0;
    z-index: 100;
  }

  .mobile-header-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .mobile-logo {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
  }

  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    z-index: 200;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    box-shadow: none;
  }

  .sidebar-open {
    transform: translateX(0);
    box-shadow: 4px 0 16px rgba(0,0,0,0.1);
  }

  .mobile-close {
    display: block;
    margin-left: auto;
    color: #909399;
    cursor: pointer;
  }

  .mobile-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.3);
    z-index: 199;
  }

  .main-content {
    padding: 12px 10px;
    max-height: none;
    overflow-y: visible;
  }

  /* 手机端弹窗全屏 */
  .el-dialog {
    width: 95% !important;
    margin: 10px auto !important;
  }

  .el-dialog .el-dialog__body {
    max-height: 60vh;
    overflow-y: auto;
  }

  /* 手机端表单标签顶部 */
  .mobile-form .el-form-item__label {
    padding-bottom: 0 !important;
    font-size: 13px;
  }

  /* 手机端日期选择器宽度 */
  .el-date-editor {
    width: 100% !important;
  }

  /* 手机端 el-row 调整 */
  .el-col-12 {
    max-width: 100% !important;
    flex: 0 0 100% !important;
  }
}
</style>
