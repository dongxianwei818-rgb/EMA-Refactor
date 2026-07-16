<template>
  <div class="login-page">
    <el-card class="login-card" shadow="always">
      <div class="login-brand">EMA</div>
      <p class="login-sub">Web 管理端登录</p>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent
      >
        <el-form-item label="用户名" prop="user_name">
          <el-input
            v-model="form.user_name"
            placeholder="请输入用户名"
            clearable
            autocomplete="username"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item label="密码" prop="psw">
          <el-input
            v-model="form.psw"
            type="password"
            placeholder="请输入密码"
            show-password
            autocomplete="current-password"
            :prefix-icon="Lock"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-alert
          v-if="error"
          type="error"
          :title="error"
          show-icon
          :closable="false"
          class="login-error"
        />
        <el-button
          type="primary"
          class="login-btn"
          :loading="loading"
          @click="onSubmit"
        >
          登录
        </el-button>
      </el-form>
      <!-- <p class="login-hint">默认管理员：admin / 123456</p> -->
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Lock, User } from "@element-plus/icons-vue";
import { loginWithPassword } from "../api/auth";

const router = useRouter();
const route = useRoute();
const formRef = ref(null);
const loading = ref(false);
const error = ref("");

const form = reactive({
  user_name: "",
  psw: "",
});

const rules = {
  user_name: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  psw: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

async function onSubmit() {
  error.value = "";
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await loginWithPassword(form.user_name.trim(), form.psw);
    const redirect =
      typeof route.query.redirect === "string" ? route.query.redirect : "/home";
    router.replace(redirect || "/home");
  } catch (e) {
    error.value = e.message || "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(circle at 15% 10%, #d9efe8 0%, transparent 40%),
    radial-gradient(circle at 85% 0%, #e8f0ed 0%, transparent 35%), #eef3f1;
}

.login-card {
  width: min(400px, 100%);
  border-radius: 16px;
  padding: 8px 4px 4px;
}

.login-brand {
  font-size: 28px;
  font-weight: 700;
  color: #0f6e5c;
  letter-spacing: 0.06em;
  text-align: center;
}

.login-sub {
  margin: 6px 0 24px;
  text-align: center;
  color: #909399;
  font-size: 14px;
}

.login-error {
  margin-bottom: 14px;
}

.login-btn {
  width: 100%;
  margin-top: 4px;
}

.login-hint {
  margin: 16px 0 0;
  text-align: center;
  font-size: 12px;
  color: #a0a8b0;
}
</style>
