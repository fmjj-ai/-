<template>
  <div>
    <a-form-item label="文本列选择">
      <a-select v-model:value="config.text_column" placeholder="选择包含文本内容的列">
        <a-select-option v-for="column in columns" :key="column" :value="column">
          {{ column }}
        </a-select-option>
      </a-select>
    </a-form-item>

    <a-form-item label="分析模型">
      <a-select v-model:value="config.method">
        <a-select-option value="snownlp">SnowNLP（本地内置）</a-select-option>
        <a-select-option value="deepseek">自定义 LLM API</a-select-option>
      </a-select>
    </a-form-item>

    <template v-if="config.method === 'deepseek'">
      <a-form-item label="API Key">
        <a-input-password v-model:value="config.api_key" placeholder="sk-..." allow-clear />
      </a-form-item>
      <a-form-item label="Base URL">
        <a-input v-model:value="config.base_url" allow-clear />
      </a-form-item>
      <a-form-item label="模型名称">
        <a-input v-model:value="config.model_name" placeholder="例如 deepseek-chat" allow-clear />
      </a-form-item>
    </template>

    <template v-else>
      <a-divider orientation="left">二次 SnowNLP</a-divider>
      <a-form-item>
        <a-checkbox v-model:checked="config.enable_second_pass_snownlp">
          启用高置信度伪标签二次训练
        </a-checkbox>
      </a-form-item>
      <a-row :gutter="12">
        <a-col :span="12">
          <a-form-item label="正向阈值">
            <a-input-number
              v-model:value="config.pseudo_label_positive_threshold"
              :min="0.5"
              :max="1"
              :step="0.05"
              style="width: 100%"
            />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="负向阈值">
            <a-input-number
              v-model:value="config.pseudo_label_negative_threshold"
              :min="0"
              :max="0.5"
              :step="0.05"
              style="width: 100%"
            />
          </a-form-item>
        </a-col>
      </a-row>
    </template>

    <a-form-item label="自定义停用词（逗号或换行分隔）">
      <a-textarea
        :value="customStopwords"
        :rows="3"
        placeholder="例如：的,了,还是,然后"
        @update:value="(v: string) => $emit('update:customStopwords', v)"
      />
    </a-form-item>

    <a-divider orientation="left">关键词与主题</a-divider>
    <a-form-item>
      <a-checkbox v-model:checked="config.extract_tfidf">提取 TF-IDF 关键词</a-checkbox>
    </a-form-item>
    <a-row :gutter="12">
      <a-col :span="12">
        <a-form-item label="TF-IDF Top K">
          <a-input-number v-model:value="config.top_k" :min="5" :max="100" style="width: 100%" />
        </a-form-item>
      </a-col>
      <a-col :span="12">
        <a-form-item>
          <a-checkbox v-model:checked="config.export_tfidf_table">导出 TF-IDF 表格</a-checkbox>
        </a-form-item>
      </a-col>
    </a-row>

    <a-form-item>
      <a-checkbox v-model:checked="config.run_lda">执行 LDA 主题提取</a-checkbox>
    </a-form-item>
    <template v-if="config.run_lda">
      <a-row :gutter="12">
        <a-col :span="8">
          <a-form-item label="最小主题数">
            <a-input-number v-model:value="config.lda_min_k" :min="2" :max="20" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="最大主题数">
            <a-input-number v-model:value="config.lda_max_k" :min="3" :max="30" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="最终 K">
            <a-input-number v-model:value="config.lda_k" :min="2" :max="20" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>
      <a-space direction="vertical" style="width: 100%">
        <a-checkbox v-model:checked="config.generate_lda_vis">生成 LDA 交互可视化</a-checkbox>
        <a-checkbox v-model:checked="config.export_lda_table">导出 LDA 结果表</a-checkbox>
      </a-space>
    </template>

    <a-divider orientation="left">词云配置</a-divider>
    <a-form-item>
      <a-checkbox v-model:checked="config.generate_wordcloud">生成词云图</a-checkbox>
    </a-form-item>
    <template v-if="config.generate_wordcloud">
      <a-form-item label="词云范围">
        <a-checkbox-group v-model:value="config.wordcloud_scopes" :options="wordcloudScopeOptions" />
      </a-form-item>
      <a-row :gutter="12">
        <a-col :span="12">
          <a-form-item label="词数上限">
            <a-input-number
              v-model:value="config.wordcloud_max_words"
              :min="20"
              :max="300"
              style="width: 100%"
            />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="字体">
            <a-select v-model:value="config.wc_font">
              <a-select-option value="Microsoft YaHei">微软雅黑</a-select-option>
              <a-select-option value="SimHei">黑体</a-select-option>
              <a-select-option value="SimSun">宋体</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item label="色卡方案">
        <a-select v-model:value="config.wordcloud_palette_key">
          <a-select-option v-for="palette in paletteOptions" :key="palette.value" :value="palette.value">
            {{ palette.label }}
          </a-select-option>
        </a-select>
        <div class="palette-preview">
          <div class="palette-label">当前颜色示意</div>
          <div class="palette-swatches">
            <span
              v-for="color in selectedPalette.colors"
              :key="color"
              class="palette-chip"
              :style="{ backgroundColor: color }"
            />
          </div>
        </div>
      </a-form-item>

      <a-form-item label="词云轮廓图">
        <a-space direction="vertical" style="width: 100%">
          <a-upload
            :show-upload-list="false"
            :custom-request="(options: any) => $emit('upload-mask', options)"
            accept=".png,.jpg,.jpeg,.webp"
          >
            <a-button block>上传轮廓图</a-button>
          </a-upload>
          <a-checkbox v-model:checked="config.wc_contour" :disabled="!maskArtifact">
            使用轮廓描边
          </a-checkbox>
          <div v-if="maskArtifact" class="mask-preview">
            <img :src="buildArtifactPreviewUrl(maskArtifact.id)" alt="mask" />
            <div class="mask-meta">
              <div>{{ maskArtifact.name }}</div>
              <a-button type="link" size="small" @click="$emit('clear-mask')">清除轮廓</a-button>
            </div>
          </div>
          <a-empty v-else :image="false" description="当前项目还没有上传轮廓图" />
        </a-space>
      </a-form-item>
    </template>

    <a-space direction="vertical" style="width: 100%">
      <a-button type="primary" block :loading="submitting" @click="$emit('start-analysis')">
        开始分析
      </a-button>
      <a-button block @click="$emit('reload-results')">刷新结果</a-button>
    </a-space>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface SentimentConfigState {
  text_column: string
  method: 'snownlp' | 'deepseek'
  api_key: string
  base_url: string
  model_name: string
  enable_second_pass_snownlp: boolean
  pseudo_label_positive_threshold: number
  pseudo_label_negative_threshold: number
  stopwords: string[]
  extract_tfidf: boolean
  top_k: number
  export_tfidf_table: boolean
  run_lda: boolean
  lda_min_k: number
  lda_max_k: number
  lda_k: number
  generate_lda_vis: boolean
  export_lda_table: boolean
  generate_wordcloud: boolean
  wordcloud_scopes: string[]
  wordcloud_max_words: number
  wordcloud_palette_key: string
  wordcloud_mask_artifact_id: number | null
  wc_font: string
  wc_contour: boolean
}

export interface PaletteOption {
  value: string
  label: string
  colors: string[]
}

const props = defineProps<{
  config: SentimentConfigState
  columns: string[]
  customStopwords: string
  maskArtifact: any | null
  submitting: boolean
  paletteOptions: PaletteOption[]
  wordcloudScopeOptions: Array<{ label: string; value: string }>
  buildArtifactPreviewUrl: (id: number) => string
}>()

defineEmits<{
  (event: 'update:customStopwords', value: string): void
  (event: 'upload-mask', options: any): void
  (event: 'clear-mask'): void
  (event: 'start-analysis'): void
  (event: 'reload-results'): void
}>()

const selectedPalette = computed(
  () =>
    props.paletteOptions.find((item) => item.value === props.config.wordcloud_palette_key) ||
    props.paletteOptions[0]
)
</script>

<style scoped>
.palette-preview {
  margin-top: 10px;
}
.palette-label {
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}
.palette-swatches {
  display: flex;
  gap: 8px;
}
.palette-chip {
  width: 26px;
  height: 14px;
  border-radius: 999px;
  border: 1px solid rgba(0, 0, 0, 0.08);
}
.mask-preview {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px;
  border-radius: 12px;
  background: rgba(244, 247, 253, 0.9);
}
.mask-preview img {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid var(--line-soft);
}
.mask-meta {
  flex: 1;
  min-width: 0;
}
</style>
