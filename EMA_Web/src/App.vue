<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand" @click="$router.push('/')">EMA Chat</div>
      <nav class="nav">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/chat">对话</RouterLink>
        <RouterLink to="/resources">资源</RouterLink>
        <RouterLink :to="{ path: '/consent', query: { mode: 'view' } }">知情同意</RouterLink>
      </nav>
    </header>
    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
</script>
