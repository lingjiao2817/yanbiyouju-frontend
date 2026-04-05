<template>
  <div class="container">
    <div class="card about-card">
      <h1 class="about-title">言必有据</h1>
      <p class="about-subtitle">AI内容事实核查助手</p>

      <div class="about-section">
        <h2>📌 项目简介</h2>
        <p>本工具基于多维统计特征分析，帮助内容创作者识别文本中疑似AI生成的部分，并提供可操作的修改建议和真实文献推荐。</p>
      </div>

      <div class="about-section">
        <h2>🔍 检测维度</h2>
        <div class="feature-grid">
          <span class="feature-tag">句长方差</span>
          <span class="feature-tag">连接词密度</span>
          <span class="feature-tag">词汇多样性</span>
          <span class="feature-tag">套话数量</span>
          <span class="feature-tag">标点多样性</span>
          <span class="feature-tag">模板短语</span>
          <span class="feature-tag">字词重复率</span>
          <span class="feature-tag">困惑度（可选）</span>
        </div>
      </div>

      <div class="about-section">
        <h2>📄 适用场景</h2>
        <ul>
          <li>大学生论文自查</li>
          <li>自媒体内容去AI味润色</li>
          <li>职场报告人性化改写</li>
        </ul>
      </div>

      <div class="about-section">
        <h2>⚠️ 免责声明</h2>
        <p>本工具基于统计特征分析，结果仅供创作前自查参考，不等同于学校或平台的官方AI检测结论。</p>
      </div>

      <div class="about-footer">
        版本 1.0.0 | 支持 .txt / .md / .docx / .pdf
      </div>
    </div>
  </div>
</template>

<style scoped>
.about-card {
  text-align: center;
}

.about-title {
  font-size: 32px;
  font-weight: 700;
  background: linear-gradient(135deg, #6d28d9, #7c3aed);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  margin-bottom: 8px;
}

.about-subtitle {
  color: #64748b;
  margin-bottom: 32px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eef2ff;
}

.about-section {
  text-align: left;
  margin-bottom: 32px;
}

.about-section h2 {
  font-size: 18px;
  color: #1e1b4b;
  margin-bottom: 12px;
}

.about-section p, .about-section ul {
  color: #475569;
  line-height: 1.6;
}

.about-section ul {
  padding-left: 20px;
}

.about-section li {
  margin: 8px 0;
}

.feature-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.feature-tag {
  background: #f1f5f9;
  padding: 6px 16px;
  border-radius: 30px;
  font-size: 13px;
  color: #1e1b4b;
}

.about-footer {
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid #eef2ff;
}
</style>