<template>
  <div class="container">
    <div class="flex flex-gap" style="align-items: flex-start;">
      <!-- 左侧输入区 -->
      <div class="card" style="flex: 1;">
        <h2 style="font-size: 18px; margin-bottom: 16px;">AI写作辅助</h2>
        <textarea 
          v-model="inputText" 
          class="assist-input"
          rows="8"
          placeholder="输入需要润色或改写的文本..."
        />
        <div class="flex" style="gap: 12px; margin-top: 16px;">
          <select v-model="style" class="style-select">
            <option value="academic">学术风格</option>
            <option value="professional">专业风格</option>
            <option value="simple">简洁风格</option>
          </select>
          <button class="btn-primary" style="flex: 1;" @click="generateSuggestion">
            生成建议
          </button>
        </div>
      </div>

      <!-- 右侧结果区 -->
      <div class="card" style="flex: 1.5;">
        <h2 style="font-size: 18px; margin-bottom: 16px;">改写建议</h2>
        <div v-if="loading" class="flex-center" style="padding: 40px;">
          <span class="spinner"></span>
          <span style="margin-left: 12px;">生成中...</span>
        </div>
        <div v-else-if="!suggestion" class="empty-state">
          暂无建议，请输入文本并点击生成
        </div>
        <div v-else class="suggestion-content">
          <div class="suggestion-box">
            <p class="suggestion-text">{{ suggestion }}</p>
          </div>
          <button class="btn-outline" style="margin-top: 16px; width: 100%;" @click="copyText">
            复制建议
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue"

const inputText = ref("")
const style = ref("academic")
const suggestion = ref("")
const loading = ref(false)

// 模拟生成建议（后续替换为真实 API）
const generateSuggestion = async () => {
  if (!inputText.value.trim()) return
  loading.value = true
  
  setTimeout(() => {
    const suggestions = {
      academic: "建议增加学术引用，调整句式结构，使用更严谨的表达方式。避免使用'首先、其次、此外'等连接词堆砌。",
      professional: "建议使用更专业的术语，保持语气正式但自然，避免模板化表达。",
      simple: "建议简化句子结构，使用更直白的表达，减少修饰词。"
    }
    suggestion.value = suggestions[style.value] + "\n\n原文本建议改写为更自然流畅的表达。"
    loading.value = false
  }, 1000)
}

const copyText = () => {
  navigator.clipboard.writeText(suggestion.value)
  alert("已复制到剪贴板")
}
</script>

<style scoped>
.assist-input {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 12px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
}

.assist-input:focus {
  outline: none;
  border-color: #6d28d9;
  box-shadow: 0 0 0 3px rgba(109, 40, 217, 0.1);
}

.style-select {
  padding: 10px 16px;
  border-radius: 40px;
  border: 1px solid #e2e8f0;
  background: white;
  font-size: 14px;
  outline: none;
}

.suggestion-content {
  background: #f8fafc;
  border-radius: 16px;
  padding: 16px;
}

.suggestion-text {
  line-height: 1.6;
  color: #334155;
  font-size: 14px;
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