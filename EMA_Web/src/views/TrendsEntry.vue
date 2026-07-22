<template>
  <AdminTrendsList v-if="admin" />
  <Trends v-else mode="all" />
</template>

<script setup>
import { isAdmin } from "../api/auth";
import AdminTrendsList from "./admin/AdminTrendsList.vue";
import Trends from "./Trends.vue";

const admin = isAdmin();
</script>
