import { computed, ref } from 'vue'
import request from '@/utils/request'
import { useAsyncAction } from './useAsyncAction'

export interface DatasetSchemaItem {
  name: string
  type: string
  [key: string]: any
}

export interface DatasetItem {
  id: number
  name: string
  status?: string
  schema_info?: DatasetSchemaItem[]
  [key: string]: any
}

const NUMERIC_KEYWORDS = ['int', 'float', 'double', 'decimal', 'long', 'short']

/**
 * 管理"选择项目下的数据集"这一通用状态。
 * - 自动过滤 status=ready 的数据集
 * - 暴露 currentDataset / columns / numericColumns 等派生值
 * - handleChange() 在切换数据集后触发 onChange 回调（各视图可用于重置面板状态）
 */
export function useDatasets(projectId: () => string, options: { onChange?: (dataset: DatasetItem | null) => void } = {}) {
  const { showError } = useAsyncAction()

  const datasets = ref<DatasetItem[]>([])
  const selectedDatasetId = ref<number | null>(null)
  const currentDataset = ref<DatasetItem | null>(null)

  const columns = computed<string[]>(() =>
    currentDataset.value?.schema_info?.map((item) => item.name) || []
  )

  const numericColumns = computed<string[]>(() => {
    const schema = currentDataset.value?.schema_info || []
    return schema
      .filter((item) => {
        const type = String(item.type || '').toLowerCase()
        return NUMERIC_KEYWORDS.some((keyword) => type.includes(keyword))
      })
      .map((item) => item.name)
  })

  const syncCurrent = () => {
    currentDataset.value = datasets.value.find((item) => item.id === selectedDatasetId.value) || null
  }

  const fetchDatasets = async () => {
    try {
      const res: any = await request.get(`/datasets/project/${projectId()}`)
      if (res.success) {
        datasets.value = res.data.filter((item: DatasetItem) => item.status === 'ready')
      }
    } catch (error: any) {
      showError(error, '获取数据集失败')
    }
  }

  const handleChange = async () => {
    syncCurrent()
    if (options.onChange) {
      await options.onChange(currentDataset.value)
    }
  }

  return {
    datasets,
    selectedDatasetId,
    currentDataset,
    columns,
    numericColumns,
    fetchDatasets,
    handleChange,
    syncCurrent,
  }
}
