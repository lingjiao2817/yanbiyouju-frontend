<script setup>
import { computed, onMounted, ref } from "vue";

// ── 演示文本（含典型AI造假声明，用于演示核查功能）──────────
const DEMO_TEXT = `据《人工智能赋能高校思政教育研究》（李明，2024）指出，大学生使用生成式AI辅助完成课程作业的比例已达67%。王磊教授认为，AI写作已经彻底改变了中国大学生的学术规范，这一趋势具有重要意义。

《教育数字化促进条例》第12条明确规定，所有高校必须在课程论文中披露AI使用痕迹。首先，相关部门正在积极研究配套措施；其次，各高校也在逐步建立内部规范；此外，学术界对此问题的讨论也日益广泛。由此可见，AI治理已成为高等教育领域不可忽视的重要议题。

综上所述，随着技术的发展，高校在推动学术诚信方面发挥着重要作用。值得注意的是，目前已有超过83%的知名高校出台了相关规定，这说明学术界对AI写作问题的重视程度正在不断提升。`;

// ── 状态 ─────────────────────────────────────────────
const form = ref({ text: "" });
const loading = ref(false);
const error = ref("");
const history = ref([]);
const currentRecord = ref(null);
const expandedParagraphs = ref(new Set());
const fileInput = ref(null);
const uploadedFile = ref(null);
const uploadedFileName = ref("");
const activeTab = ref("paragraphs");
const viewLoading = ref(false);
const inputMode = ref("text");
const activeMenu = ref(null);

// ── 计算属性 ─────────────────────────────────────────
const hasResult = computed(() => Boolean(currentRecord.value?.result));

const overallScore = computed(() =>
  currentRecord.value?.result?.overview?.score ?? 0
);

const overallRisk = computed(() =>
  currentRecord.value?.result?.overview?.risk_level ?? "low"
);

const GAUGE_R = 54;
const GAUGE_CIRCUMFERENCE = Math.PI * GAUGE_R;

const gaugeOffset = computed(() => {
  const pct = Math.max(0, Math.min(100, overallScore.value)) / 100;
  return GAUGE_CIRCUMFERENCE * (1 - pct);
});

const gaugeColor = computed(() => {
  const s = overallScore.value;
  if (s >= 65) return "#ef4444";
  if (s >= 40) return "#f59e0b";
  return "#22c55e";
});

const riskMeta = computed(() => {
  const map = {
    low:    { label: "低风险", color: "#22c55e", bg: "rgba(34,197,94,0.12)"  },
    medium: { label: "中风险", color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
    high:   { label: "高风险", color: "#ef4444", bg: "rgba(239,68,68,0.12)"  },
  };
  return map[overallRisk.value] ?? map.low;
});

const isDemoLoaded = computed(() => form.value.text === DEMO_TEXT);

// ── 生命周期 ─────────────────────────────────────────
onMounted(async () => {
  await loadHistory();
});

// ── 工具函数 ─────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const res = await fetch(path, options);
  if (res.status === 204) return null;
  let data;
  try {
    data = await res.json();
  } catch {
    throw new Error(`服务器异常（HTTP ${res.status}），文件可能过大或解析超时，请检查后端日志`);
  }
  if (!res.ok) throw new Error(data.message || "请求失败");
  return data;
}

function riskClass(level) {
  return { low: "tag-low", medium: "tag-medium", high: "tag-high" }[level] ?? "tag-low";
}

function riskLabel(level) {
  return { low: "低风险", medium: "中风险", high: "高风险" }[level] ?? level;
}

function formatDate(v) {
  return v ? v.replace("T", " ").slice(0, 16) : "";
}

function toggleParagraph(index) {
  if (expandedParagraphs.value.has(index)) {
    expandedParagraphs.value.delete(index);
  } else {
    expandedParagraphs.value.add(index);
  }
  expandedParagraphs.value = new Set(expandedParagraphs.value);
}

function paragraphBg(level) {
  const m = { low: "rgba(34,197,94,0.07)", medium: "rgba(245,158,11,0.09)", high: "rgba(239,68,68,0.10)" };
  return m[level] ?? "transparent";
}

function paragraphBorder(level) {
  const m = { low: "#22c55e", medium: "#f59e0b", high: "#ef4444" };
  return m[level] ?? "#e2e8f0";
}

// ── API 调用 ─────────────────────────────────────────
async function loadHistory() {
  try {
    const data = await apiFetch("/api/checks");
    history.value = data.items ?? [];
  } catch {}
}

async function loadRecord(id) {
  viewLoading.value = true;
  currentRecord.value = null;
  error.value = "";
  try {
    currentRecord.value = await apiFetch(`/api/checks/${id}`);
    expandedParagraphs.value = new Set();
    activeTab.value = "paragraphs";
  } catch (err) {
    showError(err.message);
  } finally {
    viewLoading.value = false;
  }
}

async function deleteRecord(id) {
  activeMenu.value = null;
  if (!confirm("确定删除这条记录？")) return;
  await apiFetch(`/api/checks/${id}`, { method: "DELETE" });
  if (currentRecord.value?.id === id) currentRecord.value = null;
  await loadHistory();
}

async function renameRecord(id, currentTitle) {
  activeMenu.value = null;
  const newTitle = prompt("请输入新标题：", currentTitle);
  if (!newTitle || newTitle.trim() === currentTitle) return;
  await apiFetch(`/api/checks/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: newTitle.trim().slice(0, 80) }),
  });
  if (currentRecord.value?.id === id) {
    currentRecord.value = { ...currentRecord.value, title: newTitle.trim().slice(0, 80) };
  }
  await loadHistory();
}

function toggleMenu(id, event) {
  event.stopPropagation();
  activeMenu.value = activeMenu.value === id ? null : id;
}

if (typeof window !== "undefined") {
  window.addEventListener("click", () => { activeMenu.value = null; });
}

async function submitCheck() {
  if (!form.value.text && !uploadedFile.value) {
    showError("请先输入文本或上传文件");
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    let record;
    if (uploadedFile.value) {
      const autoTitle = uploadedFileName.value.replace(/\.[^/.]+$/, "") || "未命名文档";
      const fd = new FormData();
      fd.append("file", uploadedFile.value);
      fd.append("title", autoTitle);
      record = await apiFetch("/api/checks", { method: "POST", body: fd });
      form.value.text = record.input_text;
    } else {
      const autoTitle = form.value.text.trim().slice(0, 12) || "未命名检测";
      record = await apiFetch("/api/checks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: autoTitle, text: form.value.text }),
      });
    }
    currentRecord.value = record;
    expandedParagraphs.value = new Set();
    activeTab.value = "paragraphs";
    clearFile();
    await loadHistory();
  } catch (err) {
    showError(err.message);
  } finally {
    loading.value = false;
  }
}

function showError(msg) {
  error.value = msg;
  setTimeout(() => { error.value = ""; }, 5000);
}

function createNew() {
  clearFile();
  form.value = { text: "" };
  currentRecord.value = null;
  error.value = "";
}

function toggleDemo() {
  if (isDemoLoaded.value) {
    clearFile();
    form.value = { text: "" };
  } else {
    clearFile();
    form.value = { text: DEMO_TEXT };
  }
}

function clearFile() {
  uploadedFile.value = null;
  uploadedFileName.value = "";
  if (fileInput.value) fileInput.value.value = "";
}

async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) { alert("文件不能超过 10MB"); return; }
  const ext = file.name.split(".").pop().toLowerCase();
  if (ext === "txt" || ext === "md") {
    clearFile();
    const reader = new FileReader();
    reader.onload = (e) => {
      form.value.text = e.target.result;
    };
    reader.readAsText(file, "UTF-8");
    return;
  }
  if (ext === "pdf" || ext === "docx") {
    uploadedFile.value = file;
    uploadedFileName.value = file.name;
    form.value.text = "";
    return;
  }
  clearFile();
  alert("支持 .txt / .md / .pdf / .docx");
}

function handleDrop(event) {
  const file = event.dataTransfer?.files?.[0];
  if (!file) return;
  handleFileUpload({ target: { files: [file] } });
}

function exportReport() {
  if (!hasResult.value) return;
  const r = currentRecord.value;
  const ov = r.result.overview;
  const lines = [
    `# AI 内容检测报告`,
    ``,
    `**标题**：${r.title}`,
    `**生成时间**：${formatDate(r.created_at)}`,
    `**整体风险**：${ov.risk_label}（${ov.score} 分）`,
    ``,
    `## 总结`,
    ov.summary,
    ``,
    `> ${ov.confidence_note}`,
    ``,
    `## 逐段分析`,
    ...r.result.paragraphs.map((p) =>
      `### 段落 ${p.index}（${riskLabel(p.risk_level)}，${p.score} 分）\n${p.text}\n\n**检测原因**：${p.reason_text}\n\n**修改方向**：${p.suggestion?.direction ?? ""}\n\n**具体建议**：\n${(p.suggestion?.actions ?? []).map((a, i) => `${i + 1}. ${a}`).join("\n")}`
    ),
  ].join("\n");

  const blob = new Blob([lines], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${r.title || "检测报告"}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}
</script>

<template>
  <div class="container">
    <div class="flex" style="gap: 24px; align-items: flex-start;">
      <!-- ========== 左侧：输入区 ========== -->
      <div class="card" style="flex: 1.2;">
        <!-- 输入模式切换 Tab -->
        <div class="input-tabs">
          <button
            :class="['input-tab', { active: inputMode === 'upload' }]"
            @click="inputMode = 'upload'"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            上传文档
          </button>
          <button
            :class="['input-tab', { active: inputMode === 'text' }]"
            @click="inputMode = 'text'"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
            </svg>
            填写文本
          </button>
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

        <!-- 上传模式 -->
        <div v-if="inputMode === 'upload'" class="upload-zone-wrap">
          <label class="upload-zone" :class="{ 'has-file': uploadedFileName }" @dragover.prevent @drop.prevent="handleDrop">
            <input ref="fileInput" type="file" accept=".txt,.md,.docx,.pdf" @change="handleFileUpload" hidden />
            <template v-if="!uploadedFileName">
              <div class="upload-icon">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="3" y="3" width="18" height="18" rx="3"/><path d="M9 12h6m-3-3v6"/>
                </svg>
              </div>
              <p class="upload-zone-title">点击或拖拽上传文档</p>
              <p class="upload-zone-sub">支持 .docx · .pdf · .txt · .md · 最大 10 MB</p>
            </template>
            <template v-else>
              <div class="upload-icon uploaded">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><polyline points="9 15 11 17 15 13"/>
                </svg>
              </div>
              <p class="upload-zone-title">{{ uploadedFileName }}</p>
              <p class="upload-zone-sub">点击重新选择文件</p>
            </template>
          </label>
          <button v-if="uploadedFileName" class="clear-file-btn" @click.prevent="clearFile">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
            移除文件
          </button>
        </div>

        <!-- 文本模式 -->
        <div v-else class="input-fields">
          <div class="field-row">
            <label class="field-label">
              文本内容
              <span class="char-count">{{ form.text.length }} 字</span>
            </label>
            <textarea
              v-model="form.text"
              class="text-area"
              rows="10"
              placeholder="粘贴 AI 生成或辅助创作的文本，系统将自动标出可疑引用、法条、数据和专家观点..."
            />
          </div>
        </div>

        <!-- 底部操作 -->
        <div class="input-footer">
          <p class="hint-line">本工具自动标出可疑引用、法条、数据，结果供提交前自查，不等同于官方结论。</p>
          <div class="footer-actions">
            <button class="btn-outline" :class="{ 'demo-active': isDemoLoaded }" @click="toggleDemo">
              {{ isDemoLoaded ? "取消示例" : "载入示例" }}
            </button>
            <button class="btn-primary" :disabled="loading" @click="submitCheck">
              <span v-if="loading" class="spinner"></span>
              {{ loading ? "检测中..." : "开始检测 →" }}
            </button>
          </div>
        </div>
      </div>

      <!-- ========== 右侧：结果区 ========== -->
      <div class="card" style="flex: 2;">
        <!-- 有结果时显示 -->
        <template v-if="hasResult">
          <!-- 概览 -->
          <div class="overview-row">
            <div class="gauge-wrap">
              <svg class="gauge-svg" viewBox="0 0 120 70">
                <path d="M 10 65 A 54 54 0 0 1 110 65" fill="none" stroke="#e2e8f0" stroke-width="10" stroke-linecap="round"/>
                <path d="M 10 65 A 54 54 0 0 1 110 65" fill="none" :stroke="gaugeColor" stroke-width="10" stroke-linecap="round" :stroke-dasharray="GAUGE_CIRCUMFERENCE" :stroke-dashoffset="gaugeOffset" style="transition: stroke-dashoffset 0.8s ease"/>
                <text x="60" y="58" text-anchor="middle" class="gauge-score" :fill="gaugeColor">{{ overallScore }}</text>
                <text x="60" y="68" text-anchor="middle" class="gauge-label">AI 概率分</text>
              </svg>
              <div class="gauge-risk" :style="{ color: riskMeta.color, background: riskMeta.bg }">
                {{ riskMeta.label }}
              </div>
            </div>

            <div class="overview-info">
              <p class="overview-summary">{{ currentRecord.result.overview.summary }}</p>
              <div class="dist-row">
                <div class="dist-item"><span class="dist-dot dot-low"></span>低风险 {{ currentRecord.result.overview.risk_distribution.low }} 段</div>
                <div class="dist-item"><span class="dist-dot dot-medium"></span>中风险 {{ currentRecord.result.overview.risk_distribution.medium }} 段</div>
                <div class="dist-item"><span class="dist-dot dot-high"></span>高风险 {{ currentRecord.result.overview.risk_distribution.high }} 段</div>
              </div>
              <div v-if="currentRecord.result.overview.claim_stats?.total" class="claim-stats-row">
                <span class="claim-stat-item stat-high">⚠ 高风险声明 {{ currentRecord.result.overview.claim_stats.high }} 处</span>
                <span class="claim-stat-item stat-medium">需核实声明 {{ currentRecord.result.overview.claim_stats.medium }} 处</span>
              </div>
              <p class="confidence-note">{{ currentRecord.result.overview.confidence_note }}</p>
            </div>

            <div class="overview-actions">
              <button class="btn-outline sm" @click="exportReport">导出报告</button>
            </div>
          </div>

          <!-- Tab 切换 -->
          <div class="tabs">
            <button :class="['tab', { active: activeTab === 'paragraphs' }]" @click="activeTab = 'paragraphs'">
              逐段分析 <span class="tab-count">{{ currentRecord.result.paragraphs.length }}</span>
            </button>
            <button :class="['tab', { active: activeTab === 'papers' }]" @click="activeTab = 'papers'">
              文献推荐 <span class="tab-count">{{ currentRecord.result.paper_recommendations?.reduce((s, r) => s + (r.items?.length ?? 0), 0) ?? 0 }}</span>
            </button>
          </div>

          <!-- 逐段分析 -->
          <div v-if="activeTab === 'paragraphs'" class="paragraphs-wrap">
            <div v-for="para in currentRecord.result.paragraphs" :key="para.index" class="para-card" :style="{ background: paragraphBg(para.risk_level), borderLeftColor: paragraphBorder(para.risk_level) }">
              <div class="para-header" @click="toggleParagraph(para.index)">
                <div class="para-meta">
                  <span class="para-idx">{{ para.index }}</span>
                  <span :class="['risk-tag', riskClass(para.risk_level)]">{{ para.risk_label }}</span>
                  <span class="para-score">{{ para.score }} 分</span>
                </div>
                <div class="para-preview">{{ para.text.slice(0, 80) }}{{ para.text.length > 80 ? "…" : "" }}</div>
                <span class="para-toggle">{{ expandedParagraphs.has(para.index) ? "收起 ▲" : "展开详情 ▼" }}</span>
              </div>

              <div v-if="expandedParagraphs.has(para.index)" class="para-detail">
                <div class="detail-section">
                  <p class="detail-label">原文</p>
                  <p class="para-fulltext">{{ para.text }}</p>
                </div>

                <div v-if="para.claims?.length" class="detail-section">
                  <p class="detail-label claim-label">⚠ 需核实声明 <span class="claim-count">{{ para.claims.length }}</span></p>
                  <div class="claim-list">
                    <div v-for="(c, i) in para.claims" :key="i" :class="['claim-item', c.risk === 'high' ? 'claim-high' : 'claim-medium']">
                      <div class="claim-top">
                        <span :class="['claim-type-tag', c.risk === 'high' ? 'ctag-high' : 'ctag-medium']">
                          {{ { citation: '文献引用', legal: '法条引用', statistic: '精确数据', authority: '专家观点' }[c.type] }}
                        </span>
                        <code class="claim-text">{{ c.text }}</code>
                      </div>
                      <p class="claim-tip">{{ c.tip }}</p>
                    </div>
                  </div>
                </div>

                <div class="detail-section">
                  <p class="detail-label">检测原因</p>
                  <ul class="reason-list"><li v-for="(r, i) in para.reasons" :key="i">{{ r }}</li></ul>
                </div>

                <div class="detail-section">
                  <p class="detail-label">特征数据</p>
                  <div class="feature-grid">
                    <div v-for="f in para.features" :key="f.key" class="feature-item">
                      <span class="feature-name">{{ f.label }}</span>
                      <span class="feature-val">{{ f.value }}</span>
                    </div>
                    <div v-if="para.perplexity !== null" class="feature-item">
                      <span class="feature-name">困惑度</span>
                      <span class="feature-val">{{ para.perplexity }}</span>
                    </div>
                  </div>
                </div>

                <div v-if="para.suggestion" class="detail-section suggestion-box">
                  <p class="detail-label">修改建议 <span class="provider-tag">{{ para.suggestion.provider }}</span></p>
                  <p class="suggestion-direction">{{ para.suggestion.direction }}</p>
                  <ol class="action-list"><li v-for="(a, i) in para.suggestion.actions" :key="i">{{ a }}</li></ol>
                  <div v-if="para.suggestion.example_rewrite" class="rewrite-example">
                    <p class="detail-label">改写示例</p>
                    <p>{{ para.suggestion.example_rewrite }}</p>
                  </div>
                  <p v-if="para.suggestion.notes?.length" class="note-line">⚠ {{ para.suggestion.notes.join("；") }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 文献推荐 -->
          <div v-if="activeTab === 'papers'" class="papers-wrap">
            <template v-for="rec in currentRecord.result.paper_recommendations" :key="rec.paragraph_index">
              <div v-if="rec.items?.length" class="paper-group">
                <p class="paper-group-title">段落 {{ rec.paragraph_index }} 的相关文献</p>
                <p class="paper-query">检索词：{{ rec.query }}</p>
                <div class="paper-list">
                  <div v-for="(paper, i) in rec.items" :key="i" class="paper-card">
                    <p class="paper-title">{{ paper.title }}</p>
                    <p class="paper-meta">{{ paper.authors }}<span v-if="paper.year"> · {{ paper.year }}</span><span v-if="paper.citations"> · 被引 {{ paper.citations }} 次</span></p>
                    <div class="paper-links">
                      <a v-if="paper.doi" :href="`https://doi.org/${paper.doi}`" target="_blank" class="paper-link">DOI</a>
                      <a v-if="paper.url" :href="paper.url" target="_blank" class="paper-link">查看原文</a>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <p v-if="!currentRecord.result.paper_recommendations?.some(r => r.items?.length)" class="empty-hint">暂无文献推荐（可能因网络原因或关键词不足）</p>
          </div>
        </template>

        <!-- 加载中 -->
        <div v-else-if="viewLoading" class="flex-center" style="padding: 60px;">
          <span class="spinner" style="width: 32px; height: 32px; border-width: 3px;"></span>
          <p style="margin-top: 16px; color: #64748b;">加载中...</p>
        </div>

        <!-- 空状态 -->
        <div v-else class="flex-center" style="flex-direction: column; padding: 60px 20px;">
          <div class="empty-illustration">
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
              <circle cx="32" cy="32" r="30" stroke="#c7d2fe" stroke-width="2"/>
              <path d="M20 32 Q32 18 44 32" stroke="#6d28d9" stroke-width="2.5" stroke-linecap="round" fill="none"/>
              <circle cx="23" cy="26" r="3" fill="#6d28d9"/>
              <circle cx="41" cy="26" r="3" fill="#6d28d9"/>
            </svg>
          </div>
          <p class="empty-title">输入文本后点击「开始检测」</p>
          <p class="empty-sub">系统将分析每个段落的 AI 生成特征，并提供可操作的修改建议。</p>
        </div>
      </div>
    </div>

    <!-- ========== 左侧边栏：历史记录 ========== -->
    <aside class="history-sidebar">
      <button class="btn-primary" style="width: 100%; margin-bottom: 20px;" @click="createNew">+ 新建检测</button>
      <p class="sidebar-title">历史记录</p>
      <div v-if="history.length" class="hist-list">
        <button v-for="item in history" :key="item.id" class="hist-item" :class="{ active: currentRecord?.id === item.id }" @click="loadRecord(item.id)">
          <div class="hist-info">
            <span class="hist-title">{{ item.title }}</span>
            <span class="hist-meta">
              <span :class="['risk-tag', riskClass(item.overall_risk)]">{{ riskLabel(item.overall_risk) }}</span>
              <span class="hist-date">{{ formatDate(item.created_at) }}</span>
            </span>
          </div>
          <div class="hist-menu-wrap" @click.stop>
            <button class="hist-more-btn" @click="toggleMenu(item.id, $event)">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>
            </button>
            <div v-if="activeMenu === item.id" class="hist-dropdown">
              <button class="hist-dropdown-item" @click="renameRecord(item.id, item.title)">重命名</button>
              <button class="hist-dropdown-item danger" @click="deleteRecord(item.id)">删除</button>
            </div>
          </div>
        </button>
      </div>
      <p v-else class="empty-hint">暂无记录</p>
    </aside>
  </div>
</template>

<style scoped>
/* 输入区样式 */
.input-tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 12px;
}

.input-tab {
  background: transparent;
  border: none;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  border-radius: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: 0.2s;
}

.input-tab.active {
  background: #eef2ff;
  color: #6d28d9;
}

.upload-zone-wrap {
  margin: 8px 0;
}

.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  border: 2px dashed #cbd5e1;
  border-radius: 20px;
  background: #fefce8;
  cursor: pointer;
  transition: 0.2s;
}

.upload-zone:hover {
  border-color: #6d28d9;
  background: #fef9c3;
}

.upload-zone.has-file {
  border-color: #6d28d9;
  background: #eef2ff;
}

.clear-file-btn {
  margin-top: 12px;
  background: #f1f5f9;
  border: none;
  border-radius: 40px;
  padding: 8px 16px;
  font-size: 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.text-area {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 14px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
}

.text-area:focus {
  outline: none;
  border-color: #6d28d9;
  box-shadow: 0 0 0 3px rgba(109, 40, 217, 0.1);
}

.input-footer {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.hint-line {
  font-size: 11px;
  color: #94a3b8;
}

.footer-actions {
  display: flex;
  gap: 12px;
}

.btn-outline.demo-active {
  background: #eef2ff;
  border-color: #6d28d9;
  color: #6d28d9;
}

.error-msg {
  background: #fee2e2;
  color: #b91c1c;
  padding: 12px;
  border-radius: 16px;
  font-size: 13px;
  margin-bottom: 16px;
}

/* 结果区样式 */
.overview-row {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eef2ff;
}

.gauge-wrap {
  text-align: center;
  min-width: 140px;
}

.gauge-svg {
  width: 120px;
  height: 70px;
}

.gauge-score {
  font-size: 28px;
  font-weight: 800;
  dominant-baseline: middle;
}

.gauge-label {
  font-size: 9px;
  fill: #64748b;
}

.gauge-risk {
  font-size: 12px;
  font-weight: 600;
  margin-top: 8px;
  padding: 4px 12px;
  border-radius: 40px;
  display: inline-block;
}

.overview-info {
  flex: 1;
}

.overview-summary {
  font-size: 14px;
  color: #334155;
  margin-bottom: 12px;
  line-height: 1.5;
}

.dist-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
}

.dist-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.dist-dot {
  width: 10px;
  height: 10px;
  border-radius: 10px;
}

.dot-low { background: #22c55e; }
.dot-medium { background: #f59e0b; }
.dot-high { background: #ef4444; }

.claim-stats-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin: 8px 0;
}

.claim-stat-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 30px;
}

.stat-high { color: #b91c1c; background: #fee2e2; }
.stat-medium { color: #b45309; background: #ffedd5; }

.confidence-note {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 6px;
}

.overview-actions {
  display: flex;
  gap: 8px;
}

.btn-outline.sm {
  padding: 6px 16px;
  font-size: 12px;
}

.tabs {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  border-bottom: 1px solid #e2e8f0;
}

.tab {
  background: transparent;
  border: none;
  padding: 8px 4px;
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tab.active {
  color: #6d28d9;
  border-bottom: 2px solid #6d28d9;
  margin-bottom: -1px;
}

.tab-count {
  background: #eef2ff;
  padding: 2px 8px;
  border-radius: 40px;
  font-size: 12px;
}

/* 段落样式 */
.paragraphs-wrap {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.para-card {
  border-left: 4px solid;
  border-radius: 16px;
  background: white;
  overflow: hidden;
}

.para-header {
  padding: 16px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.para-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.para-idx {
  font-weight: 700;
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 12px;
}

.para-preview {
  flex: 1;
  font-size: 13px;
  color: #334155;
}

.para-toggle {
  font-size: 11px;
  color: #6d28d9;
  background: #eef2ff;
  padding: 4px 12px;
  border-radius: 40px;
}

.para-detail {
  padding: 0 16px 20px 16px;
  border-top: 1px solid #f1f5f9;
}

.detail-section {
  margin-top: 20px;
}

.detail-label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  color: #64748b;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.claim-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.claim-item {
  background: #fefce8;
  border-radius: 12px;
  padding: 12px;
  border-left: 3px solid #f59e0b;
}

.claim-high {
  border-left-color: #ef4444;
  background: #fef2f2;
}

.claim-top {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}

.claim-type-tag {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 40px;
  background: #f1f5f9;
}

.ctag-high {
  background: #fee2e2;
  color: #b91c1c;
}

.ctag-medium {
  background: #ffedd5;
  color: #b45309;
}

.claim-text {
  font-family: monospace;
  font-size: 13px;
}

.claim-tip {
  font-size: 12px;
  color: #475569;
}

.reason-list {
  padding-left: 20px;
  color: #334155;
  font-size: 13px;
}

.feature-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  background: #f8fafc;
  padding: 12px;
  border-radius: 16px;
}

.feature-item {
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.suggestion-box {
  background: #f0fdf4;
  padding: 16px;
  border-radius: 16px;
}

.provider-tag {
  font-size: 10px;
  background: white;
  padding: 2px 8px;
  border-radius: 40px;
  margin-left: 8px;
}

.suggestion-direction {
  font-weight: 500;
  margin-bottom: 12px;
  font-size: 14px;
}

.action-list {
  padding-left: 20px;
  margin-bottom: 12px;
  font-size: 13px;
}

.rewrite-example {
  background: white;
  padding: 12px;
  border-radius: 12px;
  margin-top: 12px;
}

.note-line {
  font-size: 11px;
  color: #b45309;
  margin-top: 12px;
}

/* 文献推荐样式 */
.papers-wrap {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.paper-group {
  background: #f8fafc;
  border-radius: 16px;
  padding: 16px;
}

.paper-group-title {
  font-weight: 700;
  margin-bottom: 4px;
}

.paper-query {
  font-size: 11px;
  color: #64748b;
  margin-bottom: 12px;
}

.paper-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.paper-card {
  background: white;
  border-radius: 12px;
  padding: 12px;
}

.paper-title {
  font-weight: 600;
  font-size: 13px;
}

.paper-meta {
  font-size: 11px;
  color: #64748b;
}

.paper-links {
  display: flex;
  gap: 12px;
  margin-top: 6px;
}

.paper-link {
  font-size: 11px;
  color: #6d28d9;
  text-decoration: none;
}

.empty-hint {
  color: #94a3b8;
  font-size: 13px;
  padding: 20px;
  text-align: center;
}

/* 历史侧边栏 */
.history-sidebar {
  width: 280px;
  flex-shrink: 0;
  background: white;
  border-radius: 20px;
  padding: 20px;
  border: 1px solid #eef2ff;
  height: fit-content;
  position: sticky;
  top: 88px;
}

.sidebar-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  color: #94a3b8;
  margin: 0 0 12px 8px;
}

.hist-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hist-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: transparent;
  border: none;
  border-radius: 12px;
  padding: 10px;
  width: 100%;
  text-align: left;
  cursor: pointer;
  gap: 8px;
}

.hist-item:hover {
  background: #f8fafc;
}

.hist-item.active {
  background: #eef2ff;
  border-left: 3px solid #6d28d9;
}

.hist-info {
  flex: 1;
  min-width: 0;
}

.hist-title {
  font-size: 13px;
  font-weight: 500;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.hist-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 10px;
}

.hist-date {
  color: #94a3b8;
  font-size: 10px;
}

.hist-menu-wrap {
  position: relative;
}

.hist-more-btn {
  background: transparent;
  border: none;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  cursor: pointer;
  color: #94a3b8;
}

.hist-more-btn:hover {
  background: #e2e8f0;
}

.hist-dropdown {
  position: absolute;
  right: 0;
  top: 32px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1);
  border: 1px solid #e2e8f0;
  min-width: 100px;
  z-index: 20;
  overflow: hidden;
}

.hist-dropdown-item {
  display: block;
  padding: 8px 14px;
  width: 100%;
  background: white;
  border: none;
  font-size: 13px;
  cursor: pointer;
  text-align: left;
}

.hist-dropdown-item:hover {
  background: #f1f5f9;
}

.hist-dropdown-item.danger {
  color: #dc2626;
}

/* 通用 */
.risk-tag {
  padding: 2px 8px;
  border-radius: 30px;
  font-size: 11px;
  font-weight: 500;
}

.tag-low { background: rgba(34,197,94,0.12); color: #15803d; }
.tag-medium { background: rgba(245,158,11,0.12); color: #b45309; }
.tag-high { background: rgba(239,68,68,0.12); color: #b91c1c; }

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-illustration {
  margin-bottom: 16px;
}

.empty-title {
  font-weight: 500;
  margin-bottom: 8px;
  color: #1e293b;
}

.empty-sub {
  font-size: 13px;
  color: #64748b;
}

/* 响应式 */
@media (max-width: 900px) {
  .container .flex {
    flex-direction: column;
  }
  .history-sidebar {
    width: 100%;
    position: static;
    margin-top: 20px;
  }
}
</style>