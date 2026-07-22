<template>
  <div class="page-admin-user-trends">
    <div class="detail-bar">
      <div class="detail-bar-left">
        <el-button text type="primary" @click="goList"> < 返回 </el-button>
        <div class="detail-user">
          <span class="detail-name">用户名：{{ displayName }}</span>
          <span v-if="researchId" class="detail-meta"
            >研究编号： {{ researchId }}</span
          >
        </div>
      </div>
    </div>

    <Trends mode="all" :user-id="userId" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchUser } from "../../api/adminUsers";
import Trends from "../Trends.vue";

const route = useRoute();
const router = useRouter();
const profile = ref(null);

const userId = computed(() => Number(route.params.userId));
const displayName = computed(
  () => profile.value?.user_name || `用户 #${userId.value}`,
);
const researchId = computed(() => profile.value?.research_id || "");

async function loadProfile() {
  if (!userId.value) return;
  try {
    profile.value = await fetchUser(userId.value);
  } catch {
    profile.value = null;
  }
}

function goList() {
  router.push({ name: "trends" });
}

onMounted(loadProfile);
watch(userId, loadProfile);
</script>

<style scoped>
.page-admin-user-trends {
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

.detail-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
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
  font-size: 16px;
  color: #5e4dfc;
}

@media (max-width: 720px) {
  .detail-bar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
