<script setup>
import { useRouter, useRoute } from 'vue-router'

const router = useRouter();
const route = useRoute();

function goTo(page) {
  router.push(page);
}
</script>

<template>
  <div class="app-shell">
    <!-- 顶部导航 -->
    <header class="topbar">
      <div class="topbar-inner">
        <div class="logo" @click="goTo('/detect')" style="cursor: pointer;">
          <span class="logo-icon">言必有据</span>
          <span class="logo-text">AI内容事实核查助手</span>
        </div>
        <nav class="topbar-nav">
          <button class="nav-btn" @click="goTo('/detect')" :class="{ active: route.path === '/detect' }">检测中心</button>
          <button class="nav-btn" @click="goTo('/history')" :class="{ active: route.path === '/history' }">检测记录</button>
          <button class="nav-btn" @click="goTo('/recommend')" :class="{ active: route.path === '/recommend' }">文献推荐</button>
          <button class="nav-btn" @click="goTo('/assist')" :class="{ active: route.path === '/assist' }">AI写作</button>
          <button class="nav-btn" @click="goTo('/about')" :class="{ active: route.path === '/about' }">系统说明</button>
        </nav>
      </div>
    </header>

    <!-- 路由视图 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  background: #f5f3ff;
  color: #1e1b4b;
}

.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.topbar {
  background: white;
  border-bottom: 1px solid #e2e8f0;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.topbar-inner {
  max-width: 1400px;
  margin: 0 auto;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.logo-icon {
  font-weight: 700;
  font-size: 20px;
  background: linear-gradient(135deg, #6d28d9, #7c3aed);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.logo-text {
  font-size: 14px;
  color: #64748b;
}

.topbar-nav {
  display: flex;
  gap: 8px;
  align-items: center;
}

.nav-btn {
  background: transparent;
  border: none;
  padding: 8px 16px;
  margin: 0 4px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-btn:hover {
  background: #eef2ff;
  color: #6d28d9;
}

.nav-btn.active {
  background: #eef2ff;
  color: #6d28d9;
  font-weight: 600;
}

.main-content {
  flex: 1;
}
</style>