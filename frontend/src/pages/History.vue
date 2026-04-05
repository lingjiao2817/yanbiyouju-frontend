<template>
  <div class="container">
    <div class="card">
      <div class="flex-between" style="margin-bottom: 20px;">
        <h1 style="font-size: 24px; color: #1e1b4b;">检测记录</h1>
        <div class="flex" style="gap: 12px;">
          <label class="flex-center" style="gap: 8px;">
            <span style="font-size: 14px;">风险等级：</span>
            <select v-model="filterRisk" class="filter-select">
              <option value="">全部</option>
              <option value="高">高风险</option>
              <option value="中">中风险</option>
              <option value="低">低风险</option>
            </select>
          </label>
        </div>
      </div>

      <div class="history-list">
        <div 
          v-for="item in filteredRecords" 
          :key="item.id"
          class="history-item"
          @click="goDetail(item.id)"
        >
          <div class="history-item-info">
            <span class="item-title">{{ item.title }}</span>
            <span class="item-date">{{ item.date }}</span>
          </div>
          <div class="flex" style="gap: 12px; align-items: center;">
            <span :class="riskClass(item.risk)">{{ item.risk }}风险</span>
            <span class="arrow">→</span>
          </div>
        </div>
      </div>

      <div v-if="filteredRecords.length === 0" class="empty-state">
        暂无检测记录
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue"
import { useRouter } from "vue-router"

const router = useRouter()

// 假数据（后续替换为 API）
const records = ref([
  { id: 1, title: "人工智能伦理研究报告", risk: "高", date: "2026-04-01" },
  { id: 2, title: "数字化转型论文片段", risk: "中", date: "2026-04-02" },
  { id: 3, title: "教育技术应用分析", risk: "低", date: "2026-04-03" },
  { id: 4, title: "机器学习算法综述", risk: "高", date: "2026-03-28" },
  { id: 5, title: "在线教育发展现状", risk: "中", date: "2026-03-25" },
])

const filterRisk = ref("")

const filteredRecords = computed(() => {
  if (!filterRisk.value) return records.value
  return records.value.filter(r => r.risk === filterRisk.value)
})

const riskClass = (risk) => {
  if (risk === "高") return "tag-high"
  if (risk === "中") return "tag-medium"
  return "tag-low"
}

const goDetail = (id) => {
  router.push(`/history/${id}`)
}
</script>

<style scoped>
.filter-select {
  padding: 6px 12px;
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  background: white;
  font-size: 13px;
  outline: none;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #f8fafc;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  background: #eef2ff;
  transform: translateX(4px);
}

.history-item-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.item-title {
  font-weight: 500;
  font-size: 15px;
  color: #1e293b;
}

.item-date {
  font-size: 12px;
  color: #94a3b8;
}

.arrow {
  color: #94a3b8;
  font-size: 14px;
}

.empty-state {
  text-align: center;
  padding: 48px;
  color: #94a3b8;
}
</style>