<template>
  <header class="onboarding-header">
    <div class="brand">EMA</div>
    <span class="title">{{ title }}</span>
    <el-button class="logout-btn" text :loading="loggingOut" @click="onLogout">
      <el-icon :size="16"><SwitchButton /></el-icon>
      <span class="logout-label">退出</span>
    </el-button>
  </header>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { SwitchButton } from "@element-plus/icons-vue";
import { logout as logoutSession } from "../api/auth";

defineProps({
  title: { type: String, default: "" },
});

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
.onboarding-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  height: 56px;
  padding: 0 20px;
  background: #10241f;
  color: #edf7f4;
}

.brand {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.06em;
  flex-shrink: 0;
}

.title {
  flex: 1;
  text-align: center;
  font-size: 14px;
  color: #b8d4cb;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  .logout-label {
    display: none;
  }
}
</style>
