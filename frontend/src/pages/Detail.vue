<template>
  <div class="container">
    <div class="card">
      <div class="flex-between" style="margin-bottom: 24px;">
        <button class="back-btn" @click="goBack">← 返回</button>
        <h1 style="font-size: 24px; color: #1e1b4b;">检测详情</h1>
        <div style="width: 60px;"></div>
      </div>

      <!-- 基本信息 -->
      <div class="detail-section">
        <h3 class="section-title">基本信息</h3>
        <div class="info-grid">
          <div class="info-row">
            <span class="info-label">标题：</span>
            <span class="info-value">{{ record.title }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">检测时间：</span>
            <span class="info-value">{{ record.date }}</span>
          </div>
        </div>
      </div>

      <!-- 原文内容 -->
      <div class="detail-section">
        <h3 class="section-title">原文内容</h3>
        <div class="content-box">
          {{ record.content }}
        </div>
      </div>

      <!-- 风险等级 -->
      <div class="detail-section">
        <h3 class="section-title">风险等级</h3>
        <span :class="riskClass(record.risk)" style="display: inline-block; padding: 6px 20px;">
          {{ record.risk }}风险
        </span>
      </div>

      <!-- 问题分析 -->
      <div class="detail-section">
        <h3 class="section-title">问题分析</h3>
        <ul class="issue-list">
          <li v-for="(issue, idx) in record.issues" :key="idx">{{ issue }}</li>
        </ul>
      </div>

      <!-- 改写建议 -->
      <div class="detail-section">
        <h3 class="section-title">改写建议</h3>
        <ul class="suggestion-list">
          <li v-for="(s, idx) in record.suggestions" :key="idx">{{ s }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue"
import { useRoute, useRouter } from "vue-router"

const route = useRoute()
const router = useRouter()
const id = route.params.id

// 假数据映射（后续替换为 API 调用）
const fakeRecords = {
  1: {
    title: "人工智能伦理研究报告",
    date: "2026-04-01",
    content: "随着人工智能技术的快速发展，AI在学术领域的应用日益广泛。据统计，超过60%的大学生使用AI辅助完成作业。然而，这种趋势也带来了学术诚信方面的挑战。",
    risk: "高",
    issues: ["句式过于规整，AI特征明显", "缺乏具体引用来源", "连接词使用密集"],
    suggestions: ["增加真实文献引用", "调整句式多样性", "加入个人观点和数据来源说明"]
  },
  2: {
    title: "数字化转型论文片段",
    date: "2026-04-02",
    content: "企业数字化转型已成为必然趋势。首先，技术升级是基础；其次，组织变革是关键；此外，人才培养也不可忽视。",
    risk: "中",
    issues: ["连接词使用频繁", "表达略显模板化"],
    suggestions: ["简化连接词", "增加具体案例"]
  },
  3: {
    title: "教育技术应用分析",
    date: "2026-04-03",
    content: "在线教育平台为学生提供了灵活的学习方式，但同时也需要关注学习效果评估问题。",
    risk: "低",
    issues: ["部分表达略显通用"],
    suggestions: ["补充具体数据支撑"]
  }
}

const record = ref(fakeRecords[id] || fakeRecords[1])

const riskClass = (risk) => {
  if (risk === "高") return "tag-high"
  if (risk === "中") return "tag-medium"
  return "tag-low"
}

const goBack = () => {
  router.push('/history')
}
</script>

<style scoped>
.back-btn {
  background: #f1f5f9;
  border: none;
  padding: 8px 20px;
  border-radius: 30px;
  font-size: 13px;
  cursor: pointer;
  transition: 0.2s;
}

.back-btn:hover {
  background: #e2e8f0;
}

.detail-section {
  margin-bottom: 28px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #6d28d9;
  margin-bottom: 12px;
  padding-left: 10px;
  border-left: 3px solid #6d28d9;
}

.info-grid {
  background: #f8fafc;
  border-radius: 16px;
  padding: 16px;
}

.info-row {
  display: flex;
  padding: 8px 0;
}

.info-label {
  width: 100px;
  color: #64748b;
  font-size: 14px;
}

.info-value {
  color: #1e293b;
  font-size: 14px;
}

.content-box {
  background: #f8fafc;
  padding: 16px;
  border-radius: 16px;
  line-height: 1.6;
  font-size: 14px;
  color: #334155;
}

.issue-list, .suggestion-list {
  padding-left: 24px;
  margin: 0;
}

.issue-list li, .suggestion-list li {
  margin: 8px 0;
  line-height: 1.5;
  color: #334155;
}

.suggestion-list li {
  color: #6d28d9;
}
</style>