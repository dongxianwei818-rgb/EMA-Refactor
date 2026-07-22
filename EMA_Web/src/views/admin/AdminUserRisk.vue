<template>
  <div class="page-admin-user-risk">
    <div class="detail-bar">
      <div class="detail-bar-left">
        <el-button text type="primary" @click="goList">< 返回</el-button>
        <div class="detail-user">
          <span class="detail-name">用户名：{{ displayName }}</span>
          <span v-if="researchId" class="detail-meta"
            >研究编号：{{ researchId }}</span
          >
        </div>
      </div>
    </div>

    <Trends mode="risk" :user-id="userId" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchAdminRiskUserOptions } from "../../api/adminRisk";
import { fetchUser } from "../../api/adminUsers";
import Trends from "../Trends.vue";

const route = useRoute();
const router = useRouter();
const profile = ref(null);
const userOptions = ref([]);
const optionsLoading = ref(false);
const switchUserId = ref(null);

const userId = computed(() => Number(route.params.userId));
const displayName = computed(
  () => profile.value?.user_name || `用户 #${userId.value}`,
);
const researchId = computed(() => profile.value?.research_id || "");

function optionLabel(opt) {
  const name = opt.userName || `用户 #${opt.userId}`;
  return opt.researchId ? `${name}（${opt.researchId}）` : name;
}

async function loadProfile() {
  if (!userId.value) return;
  try {
    profile.value = await fetchUser(userId.value);
  } catch {
    profile.value = null;
  }
}

async function loadOptions() {
  if (!userId.value) return;
  optionsLoading.value = true;
  try {
    const data = await fetchAdminRiskUserOptions(userId.value);
    userOptions.value = Array.isArray(data) ? data : data?.items || [];
  } catch {
    userOptions.value = [];
  } finally {
    optionsLoading.value = false;
  }
}

function goList() {
  router.push({ name: "risk" });
}

function onSwitchUser(nextId) {
  if (!nextId || Number(nextId) === userId.value) {
    switchUserId.value = null;
    return;
  }
  router.push({
    name: "admin-user-risk",
    params: { userId: String(nextId) },
  });
  switchUserId.value = null;
}

onMounted(() => {
  loadProfile();
  loadOptions();
});

watch(userId, () => {
  loadProfile();
  loadOptions();
});
</script>

<style scoped>
.page-admin-user-risk {
  width: 100%;
}

.detail-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #eef0f2;
  border-radius: 12px;
}

.detail-bar-left,
.detail-bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.detail-bar-right {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.detail-user {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.detail-name {
  font-size: 16px;
  font-weight: 700;
  color: #222;
}

.detail-meta {
  margin-top: 2px;
  font-size: 14px;
  color: #cf1322;
}

.switch-label {
  font-size: 13px;
  color: #8c8c8c;
  white-space: nowrap;
}

.option-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.option-meta {
  font-size: 12px;
  color: #8c8c8c;
}

@media (max-width: 900px) {
  .detail-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .detail-bar-right {
    justify-content: stretch;
  }

  .detail-bar-right :deep(.el-select) {
    flex: 1;
    width: auto !important;
  }
}
</style>
