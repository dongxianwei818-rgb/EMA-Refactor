<template>
  <div class="task-shell">
    <header class="task-header">
      <el-button class="header-btn" text @click="$router.push('/home')"
        >< 返回首页</el-button
      >
      <span class="task-brand">EMA 打卡</span>
      <el-button
        class="header-btn logout-btn"
        text
        :loading="loggingOut"
        @click="onLogout"
      >
        退出
      </el-button>
    </header>
    <main class="task-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { logout as logoutSession } from "../api/auth";

const router = useRouter();
const loggingOut = ref(false);

async function onLogout() {
  if (loggingOut.value) return;
  loggingOut.value = true;
  try {
    await logoutSession();
  } finally {
    loggingOut.value = false;
    router.replace("/login");
  }
}
</script>

<style scoped>
.task-shell {
  min-height: 100vh;
  background: #eef3f1;
}

.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: #10241f;
  color: #edf7f4;
}

.task-brand {
  font-weight: 600;
  letter-spacing: 0.04em;
}

.header-btn {
  color: #b8d4cb !important;
}

.logout-btn {
  color: #f0c9c9 !important;
}

.task-main {
  width: min(720px, 100%);
  margin: 0 auto;
  padding: 16px;
}
</style>
