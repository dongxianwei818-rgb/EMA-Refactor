<template>
  <div class="page-chat">
    <el-card shadow="never" class="chat-card" body-class="chat-body">
      <ChatPanel />
    </el-card>
  </div>
</template>

<script setup>
import ChatPanel from '../components/ChatPanel.vue'
</script>

<style scoped>
.chat-card {
  border-radius: 16px;
  overflow: hidden;
}

.chat-card :deep(.chat-body) {
  padding: 0;
}
</style>
