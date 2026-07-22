<template>
  <el-container class="main-layout">
    <el-header class="app-header" height="56px">
      <div class="header-left">
        <div class="app-brand">EMA</div>
        <span class="app-subtitle">{{ currentTitle }}</span>
      </div>
      <div class="header-right">
        <nav class="tab-nav">
          <router-link
            v-for="tab in visibleTabs"
            :key="tab.path"
            :to="tab.path"
            class="tab-item"
            :class="{ 'is-active': isTabActive(tab.path) }"
          >
            <el-icon :size="16">
              <component :is="tab.icon" />
            </el-icon>
            <span class="tab-label">{{ tab.label }}</span>
          </router-link>
        </nav>
        <el-button
          class="logout-btn"
          text
          :loading="loggingOut"
          @click="onLogout"
        >
          <el-icon :size="16"><SwitchButton /></el-icon>
          <span class="logout-label">退出</span>
        </el-button>
      </div>
    </el-header>

    <el-main class="app-main" :class="{ 'app-main--wide': isWide }">
      <router-view :key="route.fullPath" />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  Collection,
  Document,
  House,
  Setting,
  SwitchButton,
  TrendCharts,
  User,
  Warning,
} from "@element-plus/icons-vue";
import { isAdmin, logout as logoutSession } from "../api/auth";
import { invalidateHydrateCache } from "../utils/sessionStore";

/** 普通用户顶栏 */
const userTabs = [
  { path: "/home", label: "首页", icon: House },
  { path: "/records", label: "打卡记录", icon: Document },
  { path: "/trends", label: "趋势分析", icon: TrendCharts },
  { path: "/my", label: "我的信息", icon: User },
  { path: "/resources", label: "资源分享", icon: Collection },
];

/** 管理员顶栏：趋势分析 / 风险分析 / 用户管理 + 退出 */
const adminTabs = [
  { path: "/trends", label: "趋势分析", icon: TrendCharts },
  { path: "/risk", label: "风险预警", icon: Warning },
  { path: "/users", label: "用户管理", icon: Setting },
];

const route = useRoute();
const router = useRouter();
const loggingOut = ref(false);
const visibleTabs = computed(() => (isAdmin() ? adminTabs : userTabs));
const currentTitle = computed(() => {
  if (isAdmin() && route.name === "trends") return "趋势分析";
  if (isAdmin() && route.name === "admin-user-trends") return "用户趋势详情";
  if (isAdmin() && route.name === "risk") return "风险预警";
  if (isAdmin() && route.name === "admin-user-risk") return "用户风险预警详情";
  return route.meta.title || "EMA";
});
const isWide = computed(
  () =>
    route.name === "users" ||
    route.name === "trends" ||
    route.name === "admin-user-trends" ||
    route.name === "risk" ||
    route.name === "admin-user-risk",
);

function isTabActive(path) {
  if (path === "/trends") {
    return (
      route.path === "/trends" || route.path.startsWith("/trends/")
    );
  }
  if (path === "/risk") {
    return route.path === "/risk" || route.path.startsWith("/risk/");
  }
  return route.path === path || route.path.startsWith(`${path}/`);
}

async function onLogout() {
  if (loggingOut.value) return;
  loggingOut.value = true;
  try {
    await logoutSession();
  } finally {
    invalidateHydrateCache();
    loggingOut.value = false;
    router.replace("/login");
  }
}
</script>

<style scoped>
.main-layout {
  height: 100vh;
  max-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--el-bg-color-page, #eef3f1);
}

.app-header {
  flex-shrink: 0;
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

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
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
  width: 100%;
  margin: 0 auto;
  padding: 16px;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: auto;
}

/* router-view 渲染的页面根节点铺满主内容区 */
.app-main > * {
  flex: 1;
  width: 100%;
  min-height: 0;
}

.app-main--wide {
  width: 100%;
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
  transition:
    color 0.2s,
    background 0.2s;
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

.logout-btn {
  flex-shrink: 0;
  color: #f0c9c9 !important;
  padding: 6px 10px;
  border-radius: 8px;
}

.logout-label {
  margin-left: 4px;
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

  .logout-label {
    display: none;
  }
}
</style>
