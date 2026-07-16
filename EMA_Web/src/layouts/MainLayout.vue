<template>
  <el-container class="main-layout">
    <el-header class="app-header" height="56px">
      <div class="header-left">
        <div class="app-brand">EMA</div>
        <span class="app-subtitle">{{ currentTitle }}</span>
      </div>
      <nav class="tab-nav">
        <router-link
          v-for="tab in visibleTabs"
          :key="tab.path"
          :to="tab.path"
          class="tab-item"
          active-class="is-active"
        >
          <el-icon :size="16">
            <component :is="tab.icon" />
          </el-icon>
          <span class="tab-label">{{ tab.label }}</span>
        </router-link>
      </nav>
    </el-header>

    <el-main class="app-main" :class="{ 'app-main--wide': isWide }">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  ChatDotRound,
  Collection,
  Document,
  House,
  Setting,
  TrendCharts,
  User,
} from '@element-plus/icons-vue'
import { isAdmin } from '../api/auth'

const tabs = [
  { path: '/home', label: '首页', icon: House },
  { path: '/records', label: '记录', icon: Document },
  { path: '/trends', label: '趋势', icon: TrendCharts },
  { path: '/chat', label: '对话', icon: ChatDotRound },
  { path: '/resources', label: '资源', icon: Collection },
  { path: '/users', label: '管理', icon: Setting, adminOnly: true },
  { path: '/my', label: '我的', icon: User },
]

const route = useRoute()
const visibleTabs = computed(() => tabs.filter((t) => !t.adminOnly || isAdmin()))
const currentTitle = computed(() => route.meta.title || 'EMA')
const isWide = computed(() => route.name === 'users')
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
  background: var(--el-bg-color-page, #eef3f1);
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 20px;
  background: #10241f;
  color: #edf7f4;
  border-bottom: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.app-brand {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.app-subtitle {
  font-size: 14px;
  color: #b8d4cb;
}

.app-main {
  width: min(920px, 100%);
  margin: 0 auto;
  padding: 16px;
}

.app-main--wide {
  width: min(1100px, 100%);
}

.tab-nav {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  flex-wrap: wrap;
}

.tab-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 8px;
  color: #b8d4cb;
  text-decoration: none;
  font-size: 13px;
  transition: color 0.2s, background 0.2s;
  white-space: nowrap;
}

.tab-item:hover {
  color: #edf7f4;
  background: rgba(255, 255, 255, 0.08);
}

.tab-item.is-active {
  color: #fff;
  background: rgba(255, 255, 255, 0.14);
}

.tab-label {
  line-height: 1;
}

@media (max-width: 720px) {
  .app-subtitle {
    display: none;
  }

  .tab-item {
    padding: 6px 8px;
    font-size: 12px;
  }

  .tab-label {
    display: none;
  }

  .tab-item .el-icon {
    font-size: 18px;
  }
}
</style>
