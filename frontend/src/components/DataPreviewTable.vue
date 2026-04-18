<template>
  <div class="data-preview-table">
    <div v-if="hasHorizontalOverflow" class="scroll-toolbar">
      <span class="scroll-toolbar__hint">左右查看列</span>
      <a-space size="small">
        <a-button size="small" :disabled="!canScrollLeft" @click="scrollTable(-1)">
          <template #icon>
            <LeftOutlined />
          </template>
        </a-button>
        <a-button size="small" :disabled="!canScrollRight" @click="scrollTable(1)">
          <template #icon>
            <RightOutlined />
          </template>
        </a-button>
      </a-space>
    </div>

    <div ref="containerRef" class="data-preview-table__inner">
      <a-table
        :columns="columns"
        :data-source="dataSource"
        :pagination="pagination"
        :loading="loading"
        :size="size"
        :bordered="bordered"
        :scroll="scroll"
        :row-key="rowKey"
        @change="handleChange"
      >
        <template #bodyCell="slotProps">
          <slot name="bodyCell" v-bind="slotProps">
            <span>{{ formatPreviewCellValue(slotProps.record?.[slotProps.column?.dataIndex]) }}</span>
          </slot>
        </template>
      </a-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { LeftOutlined, RightOutlined } from '@ant-design/icons-vue'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { formatPreviewCellValue } from '@/utils/previewTable'

const props = withDefaults(
  defineProps<{
    columns: any[]
    dataSource: any[]
    pagination?: any
    loading?: boolean
    size?: 'small' | 'middle' | 'large'
    bordered?: boolean
    scroll?: any
    rowKey?: string | ((record: any) => string | number)
  }>(),
  {
    pagination: undefined,
    loading: false,
    size: 'small',
    bordered: false,
    scroll: undefined,
    rowKey: undefined,
  }
)

const emit = defineEmits<{
  (event: 'change', ...args: any[]): void
}>()

const containerRef = ref<HTMLElement | null>(null)
const activeScrollElement = ref<HTMLElement | null>(null)
const hasHorizontalOverflow = ref(false)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

let resizeObserver: ResizeObserver | null = null
let syncTimer = 0

const resolveScrollElement = () => {
  if (!containerRef.value) {
    return null
  }

  const candidates = Array.from(
    containerRef.value.querySelectorAll<HTMLElement>('.ant-table-body, .ant-table-content')
  )

  return candidates.find((element) => element.scrollWidth > element.clientWidth + 1) ?? candidates[0] ?? null
}

const updateScrollState = () => {
  const element = activeScrollElement.value ?? resolveScrollElement()
  hasHorizontalOverflow.value = Boolean(element && element.scrollWidth > element.clientWidth + 1)
  canScrollLeft.value = Boolean(element && element.scrollLeft > 0)
  canScrollRight.value = Boolean(
    element && element.scrollLeft + element.clientWidth < element.scrollWidth - 1
  )
}

const bindScrollElement = () => {
  const nextElement = resolveScrollElement()
  if (activeScrollElement.value === nextElement) {
    updateScrollState()
    return
  }

  if (activeScrollElement.value) {
    activeScrollElement.value.removeEventListener('scroll', updateScrollState)
    resizeObserver?.unobserve(activeScrollElement.value)
  }

  activeScrollElement.value = nextElement

  if (activeScrollElement.value) {
    activeScrollElement.value.addEventListener('scroll', updateScrollState, { passive: true })
    resizeObserver?.observe(activeScrollElement.value)
  }

  updateScrollState()
}

const scheduleSync = () => {
  window.clearTimeout(syncTimer)
  syncTimer = window.setTimeout(() => {
    nextTick(() => {
      bindScrollElement()
    })
  }, 0)
}

const scrollTable = (direction: -1 | 1) => {
  if (!activeScrollElement.value) {
    return
  }

  const offset = Math.max(activeScrollElement.value.clientWidth * 0.8, 240) * direction
  activeScrollElement.value.scrollBy({
    left: offset,
    behavior: 'smooth',
  })
}

const handleChange = (...args: any[]) => {
  emit('change', ...args)
  scheduleSync()
}

watch(
  () => [props.columns, props.dataSource, props.loading, props.pagination, props.scroll],
  () => {
    scheduleSync()
  },
  { deep: true }
)

onMounted(() => {
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      scheduleSync()
    })
    if (containerRef.value) {
      resizeObserver.observe(containerRef.value)
    }
  }

  window.addEventListener('resize', scheduleSync)
  scheduleSync()
})

onBeforeUnmount(() => {
  window.clearTimeout(syncTimer)
  window.removeEventListener('resize', scheduleSync)

  if (activeScrollElement.value) {
    activeScrollElement.value.removeEventListener('scroll', updateScrollState)
  }

  resizeObserver?.disconnect()
  resizeObserver = null
})
</script>

<style scoped>
.data-preview-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.scroll-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
}

.scroll-toolbar__hint {
  font-size: 12px;
  color: var(--text-secondary);
}

.data-preview-table__inner {
  min-width: 0;
}
</style>
