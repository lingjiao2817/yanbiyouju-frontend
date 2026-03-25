<script setup>
import { computed, onMounted, ref } from "vue";

const demoText = `据《人工智能赋能高校思政教育研究》(李明，2024)指出，大学生使用生成式AI辅助完成课程作业的比例已达67%。
《教育数字化促进条例》第12条明确规定，所有高校必须在课程论文中披露AI使用痕迹。
王磊教授认为，AI写作已经100%改变了中国大学生的学术规范。

[1] 李明. 人工智能赋能高校思政教育研究[J]. 2024.
[2] 王磊. AI与课程论文诚信. XX大学学报, 待查.`;

const form = ref({
  title: "大学课程论文草稿",
  text: demoText,
});
const commentForm = ref({
  author: "张老师",
  role: "指导教师",
  content: "",
});
const loading = ref(false);
const commentLoading = ref(false);
const error = ref("");
const history = ref([]);
const currentRecord = ref(null);
const showBackTop = ref(false);
const fileInput = ref(null);

const categoryNames = {
  citation: "文献引用",
  law: "法条法规",
  data: "数据统计",
  entity: "人名机构",
  claim: "绝对化结论",
};
const riskNames = {
  low: "低风险",
  medium: "中风险",
  high: "高风险",
};

const categoryEntries = computed(() =>
  Object.entries(currentRecord.value?.result?.overview?.categories || {}).map(([key, value]) => ({
    key,
    label: categoryNames[key] || key,
    value,
  })),
);
const hasResult = computed(() => Boolean(currentRecord.value?.result));

onMounted(async () => {
  await loadHistory();
  if (history.value.length > 0) {
    await loadRecord(history.value[0].id);
  }
  
  // 监听滚动显示返回顶部按钮
  window.addEventListener("scroll", () => {
    showBackTop.value = window.scrollY > 200;
  });
});

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || "请求失败");
  }
  return data;
}

async function loadHistory() {
  const data = await request("/api/checks");
  history.value = data.items || [];
}

async function loadRecord(id) {
  loading.value = true;
  error.value = "";
  try {
    currentRecord.value = await request(`/api/checks/${id}`);
  } catch (err) {
    error.value = err.message;
    setTimeout(() => {
      error.value = "";
    }, 5000);
  } finally {
    loading.value = false;
  }
}

async function submitCheck() {
  loading.value = true;
  error.value = "";
  try {
    currentRecord.value = await request("/api/checks", {
      method: "POST",
      body: JSON.stringify(form.value),
    });
    await loadHistory();
  } catch (err) {
    error.value = err.message;
    setTimeout(() => {
      error.value = "";
    }, 5000);
  } finally {
    loading.value = false;
  }
}

async function submitComment() {
  if (!currentRecord.value?.id) return;

  commentLoading.value = true;
  error.value = "";
  try {
    await request(`/api/checks/${currentRecord.value.id}/comments`, {
      method: "POST",
      body: JSON.stringify(commentForm.value),
    });
    commentForm.value.content = "";
    await loadRecord(currentRecord.value.id);
  } catch (err) {
    error.value = err.message;
    setTimeout(() => {
      error.value = "";
    }, 5000);
  } finally {
    commentLoading.value = false;
  }
}

function resetDemo() {
  form.value = {
    title: "大学课程论文草稿",
    text: demoText,
  };
}

function riskClass(level) {
  return {
    low: "risk-low",
    medium: "risk-medium",
    high: "risk-high",
  }[level] || "risk-low";
}

function formatDate(value) {
  if (!value) return "";
  return value.replace("T", " ").slice(0, 16);
}

function exportReport() {
  if (!currentRecord.value?.result) return;

  const record = currentRecord.value;
  const report = [
    `# 言必有据查证报告`,
    ``,
    `标题：${record.title}`,
    `生成时间：${formatDate(record.created_at)}`,
    `整体风险：${record.result.overview.risk_label}`,
    `风险分数：${record.result.overview.score}`,
    ``,
    `## 总结`,
    `${record.result.overview.summary}`,
    `${record.result.overview.confidence_note}`,
    ``,
    `## 高风险标记`,
    ...(record.result.flags.length
      ? record.result.flags.map(
          (flag, index) =>
            `${index + 1}. [${flag.category_label}/${flag.severity_text}风险] ${flag.label}\n证据：${flag.evidence}\n说明：${flag.explanation}\n建议：${flag.suggestion}`,
        )
      : ["无明显高风险标记"]),
    ``,
    `## 核验路径建议`,
    ...record.result.verification_routes.map(
      (item, index) =>
        `${index + 1}. ${item.title}：适用于 ${item.category_label}（${item.count} 处）\n平台：${item.platforms.join(" / ")}\n操作：${item.instruction}`,
    ),
    ``,
    `## 后续操作建议`,
    ...record.result.recommended_actions.map((item, index) => `${index + 1}. ${item}`),
    ``,
    `## 教师点评`,
    ...(record.comments?.length
      ? record.comments.map(
          (item, index) =>
            `${index + 1}. ${item.role} ${item.author}（${formatDate(item.created_at)}）\n${item.content}`,
        )
      : ["暂无教师点评"]),
  ].join("\n");

  const blob = new Blob([report], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${record.title || "查证报告"}.md`;
  link.click();
  URL.revokeObjectURL(url);
  
  alert("报告已导出");
}

function scrollToResult() {
  const el = document.querySelector(".result-panel");
  if (el) {
    el.scrollIntoView({ behavior: "smooth" });
  }
}

function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}

function createNewCheck() {
  form.value = {
    title: "",
    text: "",
  };
  currentRecord.value = null;
  error.value = "";
}

// 文件上传处理
function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const fileType = file.name.split('.').pop().toLowerCase();
  const fileSize = file.size / 1024 / 1024; // MB

  // 检查文件大小（限制 10MB）
  if (fileSize > 10) {
    alert('文件过大，请上传小于 10MB 的文件');
    return;
  }

  // 处理纯文本文件
  if (fileType === 'txt' || fileType === 'md') {
    const reader = new FileReader();
    reader.onload = (e) => {
      form.value.text = e.target.result;
      if (!form.value.title) {
        form.value.title = file.name.replace(/\.[^/.]+$/, "");
      }
    };
    reader.onerror = () => {
      alert('文件读取失败，请重试');
    };
    reader.readAsText(file, 'UTF-8');
    return;
  }

  // .docx 和 .pdf 暂不支持直接读取内容
  if (fileType === 'docx' || fileType === 'pdf') {
    alert(`暂不支持直接读取 ${fileType.toUpperCase()} 文件内容，请转换为 .txt 或 .md 格式后上传，或直接粘贴文本。\n\n文件名：${file.name}`);
    if (!form.value.title) {
      form.value.title = file.name.replace(/\.[^/.]+$/, "");
    }
    return;
  }

  alert('请上传 .txt、.md、.docx 或 .pdf 格式的文件');
}
</script>

<template>
  <div class="page-shell">
    <header class="hero">
      <div class="hero-copy">
        <p class="eyebrow">课程论文 / 作业 AI 查证助手</p>
        <h1>《言必有据》</h1>
        <p class="hero-text">
          不判断是不是 AI 写的，只检查 AI 文本里哪些文献、数据、法条和人名背书值得怀疑。
        </p>
      </div>
      <div class="hero-card">
        <p>适用场景</p>
        <ul>
          <li>课程论文初稿自查</li>
          <li>小组作业引用核验</li>
          <li>教师快速定位高风险内容</li>
        </ul>
      </div>
    </header>

    <div class="layout">
      <!-- 左侧侧边栏 -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <h2>言必有据</h2>
          <p>AI文本查证助手</p>
        </div>

        <button class="primary-button full" @click="createNewCheck">
          + 新建查证
        </button>

        <div class="section-head tight">
          <div>
            <p class="section-kicker">Step 2</p>
            <h2>历史记录</h2>
          </div>
        </div>

        <div class="history-list" v-if="history.length">
          <button
            v-for="item in history"
            :key="item.id"
            class="history-item"
            type="button"
            @click="loadRecord(item.id)"
          >
            <span class="history-title">{{ item.title }}</span>
            <span class="history-meta">
              <strong :class="['risk-pill', riskClass(item.overall_risk)]">
                {{ riskNames[item.overall_risk] || item.overall_risk }}
              </strong>
              {{ formatDate(item.created_at) }}
            </span>
            <span
              class="history-summary"
              :title="item.summary"
            >
              {{ item.summary.slice(0, 25) }}{{ item.summary.length > 25 ? "..." : "" }}
            </span>
          </button>
        </div>
        <p v-else class="empty-state">提交一次查证后，这里会显示最近记录。</p>
      </aside>

      <!-- 右侧主内容区 -->
      <div class="main-content">
        <section class="card editor">
          <div class="section-head">
            <div>
              <p class="section-kicker">Step 1</p>
              <h2>粘贴 AI 生成文本</h2>
            </div>
            <div class="editor-actions">
              <button class="ghost-button" type="button" @click="resetDemo">
                载入示例
              </button>

              <!-- 上传文件按钮 -->
              <label class="ghost-button file-upload">
                📁 上传文件
                <input 
                  type="file" 
                  accept=".txt,.md,.docx,.pdf" 
                  @change="handleFileUpload" 
                  hidden 
                />
              </label>

              <button
                class="primary-button"
                type="button"
                :disabled="loading"
                @click="submitCheck"
              >
                <span v-if="loading" class="spinner"></span>
                {{ loading ? "核查中..." : "🔍 开始查证" }}
              </button>

              <button class="ghost-button" type="button" @click="scrollToResult">
                ↓ 查看结果
              </button>
            </div>
          </div>

          <label class="field">
            <span>任务标题</span>
            <input
              v-model="form.title"
              type="text"
              maxlength="120"
              placeholder="例如：人工智能课程论文草稿"
            />
            <div class="char-count">
              当前字数：{{ form.title.length }} / 120
            </div>
          </label>

          <label class="field">
            <span>待核查文本</span>
            <textarea
              v-model="form.text"
              rows="8"
              style="resize: vertical; white-space: pre-wrap;"
              placeholder="建议每次提交 500–2000 字，核查效果最佳..."
            />
            <div class="char-count">
              当前字数：{{ form.text.length }} 字
            </div>
          </label>

          <p class="hint">
            当前版本是离线规则核查。它负责圈出“像真的但可能不对”的部分，最终仍需要你去真实数据库核对。
          </p>
        </section>

        <section class="card result-panel">
          <div class="section-head">
            <div>
              <p class="section-kicker">Step 3</p>
              <h2>核查结果</h2>
            </div>
            <button class="ghost-button" type="button" :disabled="!hasResult" @click="exportReport">
              导出报告
            </button>
          </div>

          <p v-if="error" class="error-banner">{{ error }}</p>

          <template v-if="hasResult">
            <div class="summary-grid">
              <article class="summary-card emphasis">
                <p class="mini-label">整体风险</p>
                <div class="summary-value">
                  <span :class="['risk-pill', riskClass(currentRecord.result.overview.risk_level)]">
                    {{ currentRecord.result.overview.risk_label }}
                  </span>
                  <strong>{{ currentRecord.result.overview.score }}</strong>
                </div>
                <p>{{ currentRecord.result.overview.summary }}</p>
                <p class="summary-note">{{ currentRecord.result.overview.confidence_note }}</p>
              </article>

              <article class="summary-card" v-for="item in categoryEntries" :key="item.key">
                <p class="mini-label">{{ item.label }}</p>
                <strong>{{ item.value }}</strong>
                <span>处需要复核</span>
              </article>
            </div>

            <div class="content-grid">
              <section class="subpanel">
                <div class="subpanel-head">
                  <h3>高风险标记</h3>
                  <span>{{ currentRecord.result.flags.length }} 项</span>
                </div>
                <div v-if="currentRecord.result.flags.length" class="flag-list">
                  <article v-for="(flag, index) in currentRecord.result.flags" :key="`${flag.label}-${index}`" class="flag-card">
                    <div class="flag-top">
                      <span :class="['risk-pill', riskClass(flag.severity)]">{{ flag.severity_text }}风险</span>
                      <span class="tag">{{ flag.category_label }}</span>
                    </div>
                    <h4>{{ flag.label }}</h4>
                    <blockquote>{{ flag.evidence }}</blockquote>
                    <p>{{ flag.explanation }}</p>
                    <small>建议：{{ flag.suggestion }}</small>
                  </article>
                </div>
                <p v-else class="empty-state">暂未发现明显高风险项。</p>
              </section>

              <section class="subpanel">
                <div class="subpanel-head">
                  <h3>段落视图</h3>
                  <span>{{ currentRecord.result.paragraphs.length }} 段</span>
                </div>
                <div class="paragraph-list">
                  <article
                    v-for="paragraph in currentRecord.result.paragraphs"
                    :key="paragraph.index"
                    class="paragraph-card"
                  >
                    <div class="flag-top">
                      <span class="tag">段落 {{ paragraph.index }}</span>
                      <span :class="['risk-pill', riskClass(paragraph.risk_level)]">
                        {{ riskNames[paragraph.risk_level] || paragraph.risk_level }}
                      </span>
                    </div>
                    <p class="paragraph-text">{{ paragraph.text }}</p>
                    <p v-if="paragraph.notes.length" class="paragraph-note">
                      {{ paragraph.notes.join("；") }}
                    </p>
                  </article>
                </div>
              </section>
            </div>

            <div class="content-grid secondary-grid">
              <section class="subpanel">
                <div class="subpanel-head">
                  <h3>核验路径建议</h3>
                  <span>{{ currentRecord.result.verification_routes.length }} 条</span>
                </div>
                <div class="route-list">
                  <article
                    v-for="(item, index) in currentRecord.result.verification_routes"
                    :key="`${item.title}-${index}`"
                    class="route-card"
                  >
                    <div class="flag-top">
                      <span class="tag">{{ item.category_label }}</span>
                      <span class="route-count">{{ item.count }} 处</span>
                    </div>
                    <h4>{{ item.title }}</h4>
                    <p>{{ item.instruction }}</p>
                    <p class="route-platforms">推荐来源：{{ item.platforms.join(" / ") }}</p>
                  </article>
                </div>
              </section>

              <section class="subpanel">
                <div class="subpanel-head">
                  <h3>后续操作建议</h3>
                  <span>{{ currentRecord.result.recommended_actions.length }} 条</span>
                </div>
                <ol class="action-list">
                  <li v-for="(item, index) in currentRecord.result.recommended_actions" :key="`${item}-${index}`">
                    {{ item }}
                  </li>
                </ol>
              </section>
            </div>

            <section class="subpanel reference-panel">
              <div class="subpanel-head">
                <h3>参考文献检查</h3>
                <span>{{ currentRecord.result.reference_checks.length }} 条</span>
              </div>
              <div v-if="currentRecord.result.reference_checks.length" class="reference-list">
                <article
                  v-for="(item, index) in currentRecord.result.reference_checks"
                  :key="`${item.line}-${index}`"
                  class="reference-card"
                >
                  <div class="flag-top">
                    <span :class="['risk-pill', riskClass(item.risk_level)]">
                      {{ riskNames[item.risk_level] || item.risk_level }}
                    </span>
                  </div>
                  <p class="reference-line">{{ item.line }}</p>
                  <p class="reference-note">{{ item.notes.join("；") || "字段完整度较高" }}</p>
                </article>
              </div>
              <p v-else class="empty-state">当前文本没有识别到标准参考文献行。</p>
            </section>

            <section class="subpanel comment-panel">
              <div class="subpanel-head">
                <h3>教师点评</h3>
                <span>{{ currentRecord.comments?.length || 0 }} 条</span>
              </div>

              <div class="comment-form">
                <label class="field inline-field">
                  <span>点评人</span>
                  <input v-model="commentForm.author" type="text" maxlength="40" placeholder="例如：张老师" />
                </label>
                <label class="field inline-field">
                  <span>身份</span>
                  <input v-model="commentForm.role" type="text" maxlength="40" placeholder="例如：指导教师" />
                </label>
                <label class="field">
                  <span>点评内容</span>
                  <textarea
                    v-model="commentForm.content"
                    rows="4"
                    maxlength="1000"
                    placeholder="可以记录教师建议、答辩意见或修改要求"
                  />
                </label>
                <button class="primary-button" type="button" :disabled="commentLoading" @click="submitComment">
                  {{ commentLoading ? "提交中..." : "保存点评" }}
                </button>
              </div>

              <div v-if="currentRecord.comments?.length" class="comment-list">
                <article v-for="item in currentRecord.comments" :key="item.id" class="comment-card">
                  <div class="flag-top">
                    <div>
                      <strong>{{ item.author }}</strong>
                      <span class="comment-role">{{ item.role }}</span>
                    </div>
                    <span class="comment-time">{{ formatDate(item.created_at) }}</span>
                  </div>
                  <p>{{ item.content }}</p>
                </article>
              </div>
              <p v-else class="empty-state">还没有点评记录，可以先添加一条示范意见。</p>
            </section>
          </template>

          <p v-else class="empty-state">
            📭 暂无核查结果<br />
            请在上方输入文本并点击「开始查证」
          </p>
        </section>
      </div>
    </div>

    <!-- 返回顶部按钮 -->
    <button v-if="showBackTop" class="back-top" @click="scrollToTop">
      ↑
    </button>
  </div>
</template>