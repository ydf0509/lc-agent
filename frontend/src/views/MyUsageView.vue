<template>
  <div class="my-usage usage-page">
    <div class="page-header">
      <h2>我的用量</h2>
    </div>

    <div class="filter-bar">
      <el-date-picker
        v-model="range"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        :clearable="false"
        class="f-date"
        @change="load"
      />
      <el-select v-model="granularity" class="f-gran" @change="load">
        <el-option label="按天" value="day" />
        <el-option label="按月" value="month" />
      </el-select>
      <el-select v-model="groupBy" multiple collapse-tags class="f-group" placeholder="分组维度" @change="load">
        <el-option label="Agent" value="agent" />
        <el-option label="模型" value="model_id" />
      </el-select>
      <el-checkbox v-model="includeSub" @change="load">含子 Agent</el-checkbox>
      <el-button type="primary" :loading="loading" @click="load">查询</el-button>
    </div>

    <div class="cards">
      <div class="stat-card stat-card--cost">
        <div class="stat-label">期间消耗（元）</div>
        <div class="stat-value">{{ fmtCost(totals?.cost) }}</div>
        <div v-if="totals && totals.cost === null" class="cost-hint">{{ unpricedHint }}</div>
      </div>
      <div class="stat-card stat-card--tokens">
        <div class="stat-label">期间 Token</div>
        <div class="stat-value">{{ fmtNum(totalTokens) }}</div>
      </div>
      <div class="stat-card stat-card--calls">
        <div class="stat-label">调用次数</div>
        <div class="stat-value">{{ fmtNum(totals?.calls ?? 0) }}</div>
      </div>
    </div>

    <el-table v-loading="loading" :data="rows" stripe border max-height="520">
      <el-table-column
        v-for="dim in displayDims"
        :key="dim"
        :prop="dim"
        :label="dimLabel(dim)"
        min-width="110"
      />
      <el-table-column label="输入" min-width="100" align="right">
        <template #default="{ row }">{{ fmtNum(row.input_tokens) }}</template>
      </el-table-column>
      <el-table-column label="命中缓存" min-width="100" align="right">
        <template #default="{ row }">{{ fmtNum(row.cache_read_tokens) }}</template>
      </el-table-column>
      <el-table-column label="写入缓存" min-width="100" align="right">
        <template #default="{ row }">{{ fmtNum(row.cache_write_tokens) }}</template>
      </el-table-column>
      <el-table-column label="输出" min-width="100" align="right">
        <template #default="{ row }">{{ fmtNum(row.output_tokens) }}</template>
      </el-table-column>
      <el-table-column prop="calls" label="调用" width="80" align="right" />
      <el-table-column label="金额（元）" min-width="110" align="right">
        <template #default="{ row }">
          <el-tooltip v-if="row.cost === null" :content="unpricedTip(row.unpriced_models)" placement="top">
            <span class="unpriced">—</span>
          </el-tooltip>
          <span v-else>{{ fmtCost(row.cost) }}</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type UsageSummaryRow, type UsageTotals } from '@/api/http'

const today = new Date().toISOString().slice(0, 10)
const monthStart = today.slice(0, 8) + '01'

const range = ref<[string, string]>([monthStart, today])
const granularity = ref<'day' | 'month'>('day')
// 时间列永远显示（粒度由 granularity 控制），分组：Agent / 模型（多选，可单选多选或都不选）
const groupBy = ref<string[]>(['agent'])
const includeSub = ref(true)

const displayDims = computed(() => {
  const dims = groupBy.value.filter((d) => d !== 'bucket')
  return ['bucket', ...dims]
})

function dimLabel(dim: string): string {
  const labels: Record<string, string> = {
    agent: 'Agent', model_id: '模型', bucket: '时间',
  }
  return labels[dim] || dim
}

const loading = ref(false)
const rows = ref<UsageSummaryRow[]>([])
const totals = ref<UsageTotals | null>(null)

// 未配价模型名单（后端给）：费用显示 — 时说明原因
const unpricedModels = ref<string[]>([])
const unpricedHint = computed(() =>
  unpricedModels.value.length > 0
    ? `${unpricedModels.value.length} 个模型未设置单价，费用暂时算不出来（请联系管理员设置）`
    : '有模型未设置单价，费用暂时算不出来（请联系管理员设置）'
)

const totalTokens = computed(() =>
  // input_tokens 已含命中/写入缓存明细（langchain 口径），直接相加会重复统计
  (totals.value?.input_tokens ?? 0) + (totals.value?.output_tokens ?? 0)
)

function fmtNum(n: number | undefined): string {
  return (n ?? 0).toLocaleString('zh-CN')
}

function fmtCost(c: number | null | undefined): string {
  if (c === null || c === undefined) return '—'
  // 后端保留 4 位小数；小额费用 2 位会显示 ¥0.00，智能提升精度
  return `¥${c < 0.01 && c > 0 ? c.toFixed(4) : c.toFixed(2)}`
}

// 金额为 — 时的提示：哪个模型没设单价
function unpricedTip(names?: string[]): string {
  const list = (names ?? []).join('、')
  return list ? `未设置单价的模型：${list}` : '有模型未设置单价，这一行金额算不出来'
}

async function load() {
  loading.value = true
  try {
    const [from, to] = range.value
    const result = await api.getMyUsage({
      from, to, group_by: groupBy.value.join(',') || 'bucket',
      granularity: granularity.value,
      include_sub: includeSub.value,
    })
    rows.value = result.rows
    totals.value = result.totals
    unpricedModels.value = result.unpriced_models ?? []
  } catch (e: any) {
    ElMessage.error(e.message || '加载用量失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.my-usage {
  padding: 20px 28px;
  max-width: 1080px;
  margin: 0 auto;
}
.page-header h2 {
  margin: 0 0 16px;
}
.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 18px;
}
.stat-card {
  position: relative;
  padding: 14px 18px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-bg-color);
  overflow: hidden;
}
.stat-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--card-accent, var(--el-color-primary));
}
.stat-card--cost {
  --card-accent: #6366f1;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), transparent 65%);
  border-color: rgba(99, 102, 241, 0.35);
}
.stat-card--cost .stat-value {
  color: #818cf8;
  font-size: 26px;
}
.stat-card--tokens {
  --card-accent: #06b6d4;
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.10), transparent 65%);
  border-color: rgba(6, 182, 212, 0.30);
}
.stat-card--tokens .stat-value {
  color: #22d3ee;
}
.stat-card--calls {
  --card-accent: #10b981;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.10), transparent 65%);
  border-color: rgba(16, 185, 129, 0.30);
}
.stat-card--calls .stat-value {
  color: #34d399;
}
.stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}
.stat-value {
  font-size: 22px;
  font-weight: 600;
}
.unpriced {
  color: var(--el-text-color-secondary);
}
.cost-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-color-warning);
}
</style>

<style>
/* 非 scoped：筛选控件样式（.usage-page 圈定范围） */
.filter-bar {
  padding: 12px 14px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  background: var(--el-bg-color);
}
.usage-page .filter-bar .el-date-editor,
.usage-page .filter-bar .el-select {
  flex: none;
}
.usage-page .f-date {
  width: 300px;
}
.usage-page .f-gran {
  width: 104px;
}
.usage-page .f-group {
  width: 150px;
}
.usage-page .filter-bar .el-input__wrapper,
.usage-page .filter-bar .el-select__wrapper {
  border-radius: 8px;
  background: var(--el-fill-color-light);
  box-shadow: 0 0 0 1px color-mix(in srgb, #818cf8 28%, var(--el-border-color)) inset;
}
.usage-page .filter-bar .el-input__wrapper:hover,
.usage-page .filter-bar .el-select__wrapper:hover {
  box-shadow: 0 0 0 1px color-mix(in srgb, #818cf8 55%, var(--el-border-color)) inset;
}
.usage-page .filter-bar .el-input__wrapper.is-focus,
.usage-page .filter-bar .el-select__wrapper.is-focused {
  box-shadow: 0 0 0 1px #818cf8 inset;
}
</style>
