<template>
  <div class="login-page">
    <el-card class="login-card" shadow="always">
      <div class="login-brand">EMA</div>
      <p class="login-sub">大学生心理健康 EMA 研究系统</p>

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
        <el-button
          text
          type="primary"
          class="change-pwd-link"
          @click="openChangePwd"
        >
          修改密码
        </el-button>
      </el-form>
    </el-card>

    <el-dialog
      v-model="pwdDialogVisible"
      title="修改密码"
      width="400px"
      destroy-on-close
      align-center
      @closed="resetPwdForm"
    >
      <el-form
        ref="pwdFormRef"
        :model="pwdForm"
        :rules="pwdRules"
        label-position="top"
        @submit.prevent
      >
        <el-form-item label="用户名" prop="user_name">
          <el-input
            v-model="pwdForm.user_name"
            placeholder="请输入用户名"
            clearable
            autocomplete="username"
          />
        </el-form-item>
        <el-form-item label="原密码" prop="old_psw">
          <el-input
            v-model="pwdForm.old_psw"
            type="password"
            placeholder="请输入原密码"
            show-password
            autocomplete="current-password"
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_psw">
          <el-input
            v-model="pwdForm.new_psw"
            type="password"
            placeholder="至少 6 位"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_psw">
          <el-input
            v-model="pwdForm.confirm_psw"
            type="password"
            placeholder="请再次输入新密码"
            show-password
            autocomplete="new-password"
            @keyup.enter="onChangePassword"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="pwdLoading"
          @click="onChangePassword"
        >
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Lock, User } from "@element-plus/icons-vue";
import {
  changePassword,
  fetchProfile,
  isAdmin,
  loginWithPassword,
} from "../api/auth";
import {
  applyConsentFromServer,
  hasConsent,
  setServerProfile,
} from "../utils/consentState";
import { isResearchBound } from "../utils/ema";
import { hydrateFromServer } from "../utils/hydrate";
import { markOnboardingSynced } from "../utils/onboardingGate";

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

const pwdDialogVisible = ref(false);
const pwdLoading = ref(false);
const pwdFormRef = ref(null);
const pwdForm = reactive({
  user_name: "",
  old_psw: "",
  new_psw: "",
  confirm_psw: "",
});

const validateConfirm = (_rule, value, callback) => {
  if (!value) {
    callback(new Error("请再次输入新密码"));
    return;
  }
  if (value !== pwdForm.new_psw) {
    callback(new Error("两次输入的新密码不一致"));
    return;
  }
  callback();
};

const pwdRules = {
  user_name: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  old_psw: [{ required: true, message: "请输入原密码", trigger: "blur" }],
  new_psw: [
    { required: true, message: "请输入新密码", trigger: "blur" },
    { min: 6, message: "新密码至少 6 位", trigger: "blur" },
  ],
  confirm_psw: [{ validator: validateConfirm, trigger: "blur" }],
};

function openChangePwd() {
  pwdForm.user_name = form.user_name.trim();
  pwdForm.old_psw = "";
  pwdForm.new_psw = "";
  pwdForm.confirm_psw = "";
  pwdDialogVisible.value = true;
}

function resetPwdForm() {
  pwdForm.user_name = "";
  pwdForm.old_psw = "";
  pwdForm.new_psw = "";
  pwdForm.confirm_psw = "";
  pwdFormRef.value?.resetFields?.();
}

async function onChangePassword() {
  const valid = await pwdFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  pwdLoading.value = true;
  try {
    await changePassword(
      pwdForm.user_name.trim(),
      pwdForm.old_psw,
      pwdForm.new_psw.trim(),
    );
    ElMessage.success("密码修改成功，请使用新密码登录");
    form.user_name = pwdForm.user_name.trim();
    form.psw = "";
    pwdDialogVisible.value = false;
  } catch (e) {
    ElMessage.error(e.message || "修改密码失败");
  } finally {
    pwdLoading.value = false;
  }
}

async function resolvePostLoginPath() {
  if (isAdmin()) return "/trends";

  try {
    const profile = await fetchProfile();
    if (profile) {
      setServerProfile({
        research_id: profile.research_id,
        has_baseline: profile.has_baseline,
        has_consent: profile.has_consent,
        study_status: profile.study_status,
      });
      if (typeof profile.has_consent === "boolean") {
        applyConsentFromServer({
          has_consent: profile.has_consent,
          status: profile.has_consent ? "accept" : null,
          at: profile.consent_at || null,
        });
      }
      markOnboardingSynced();
      if (!profile.has_consent && !hasConsent()) return "/consent";
      if (!profile.has_baseline && !isResearchBound()) return "/baseline";
      // 登录后全量拉取服务端业务数据，保证换设备数据一致
      try {
        await hydrateFromServer({ force: true });
      } catch (e) {
        console.warn("登录后同步用户数据失败", e);
      }
    }
  } catch {
    /* fall through to local checks */
  }

  if (!hasConsent()) return "/consent";
  if (!isResearchBound()) return "/baseline";

  const redirect =
    typeof route.query.redirect === "string" ? route.query.redirect : "";
  if (redirect && redirect !== "/login") return redirect;
  return "/home";
}

async function onSubmit() {
  error.value = "";
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await loginWithPassword(form.user_name.trim(), form.psw);
    const path = await resolvePostLoginPath();
    router.replace(path);
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

.change-pwd-link {
  display: block;
  width: 100%;
  margin-top: 8px;
  margin-left: 0;
}

.login-hint {
  margin: 16px 0 0;
  text-align: center;
  font-size: 12px;
  color: #a0a8b0;
}
</style>
