<template>
  <div class="container">
    <div class="flex flex-gap" style="align-items: flex-start;">
      <!-- 左侧输入区 -->
      <div class="card" style="flex: 1;">
        <h2 style="font-size: 18px; margin-bottom: 16px;">文献检索</h2>
        <textarea 
          v-model="queryText" 
          class="recommend-input"
          rows="6"
          placeholder="粘贴文本或输入关键词，系统将推荐相关学术文献..."
        />
        <button class="btn-primary" style="margin-top: 16px; width: 100%;" @click="searchPapers">
          推荐文献
        </button>
      </div>

      <!-- 右侧结果区 -->
      <div class="card" style="flex: 1.5;">
        <h2 style="font-size: 18px; margin-bottom: 16px;">文献推荐</h2>
        <div v-if="loading" class="flex-center" style="padding: 40px;">
          <span class="spinner"></span>
          <span style="margin-left: 12px;">搜索中...</span>
        </div>
        <div v-else-if="papers.length === 0" class="empty-state">
          暂无文献推荐，请输入文本或关键词
        </div>
        <div v-else class="papers-list">
          <div v-for="(paper, idx) in papers" :key="idx" class="paper-item">
            <div class="paper-title">{{ paper.title }}</div>
            <div class="paper-meta">{{ paper.authors }} · {{ paper.year }} · 被引 {{ paper.citations }} 次</div>
            <a v-if="paper.url" :href="paper.url" target="_blank" class="paper-link">查看原文 →</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue"

const queryText = ref("")
const papers = ref([])
const loading = ref(false)

// 模拟文献推荐（后续替换为真实 API）
const searchPapers = async () => {
  if (!queryText.value.trim()) return
  loading.value = true
  
  // 模拟 API 请求延迟
  setTimeout(() => {
    papers.value = [
      { title: "人工智能在学术写作中的应用研究", authors: "李明, 王华", year: "2024", citations: 56, url: "#" },
      { title: "AI生成内容的检测方法综述", authors: "张伟, 陈思", year: "2023", citations: 89, url: "#" },
      { title: "学术诚信与人工智能伦理", authors: "赵敏", year: "2024", citations: 34, url: "#" }
    ]
    loading.value = false
  }, 1000)
}
</script>

<style scoped>
.recommend-input {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 12px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
}

.recommend-input:focus {
  outline: none;
  border-color: #6d28d9;
  box-shadow: 0 0 0 3px rgba(109, 40, 217, 0.1);
}

.papers-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.paper-item {
  padding: 12px;
  background: #f8fafc;
  border-radius: 12px;
}

.paper-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 6px;
  color: #1e293b;
}

.paper-meta {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 8px;
}

.paper-link {
  font-size: 12px;
  color: #6d28d9;
  text-decoration: none;
}

.empty-state {
  text-align: center;
  padding: 48px;
  color: #94a3b8;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #e2e8f0;
  border-top-color: #6d28d9;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>