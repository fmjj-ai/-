import { message } from 'ant-design-vue'
import request from '@/utils/request'
import { useAsyncAction } from './useAsyncAction'

export interface ChartExposable {
  getChartDataUrl?: (type: 'png' | 'svg', transparent?: boolean, pixelRatio?: number) => string
}

const dataUrlToFile = async (dataUrl: string, filename: string) => {
  const response = await fetch(dataUrl)
  const blob = await response.blob()
  return new File([blob], filename, { type: blob.type || 'application/octet-stream' })
}

/**
 * 把 Chart.vue 实例里的图表导出并作为 artifact 上传到后端（导出中心）。
 * chartRefGetter 返回当前视图里那个 Chart 组件的实例。
 */
export function useChartArtifactExport(options: {
  chartRefGetter: () => ChartExposable | null | undefined
  projectId: () => string
  buildFileName: (type: 'png' | 'svg') => string
}) {
  const { showError } = useAsyncAction()

  const exportChartArtifact = async (type: 'png' | 'svg') => {
    const chart = options.chartRefGetter()
    const dataUrl = chart?.getChartDataUrl?.(type, false, 2)
    if (!dataUrl) {
      message.warning('当前没有可导出的图表')
      return
    }
    try {
      const filename = options.buildFileName(type)
      const file = await dataUrlToFile(dataUrl, filename)
      const formData = new FormData()
      formData.append('project_id', options.projectId())
      formData.append('name', filename)
      formData.append('file', file)
      const res: any = await request.post('/artifacts/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      if (res.success) {
        message.success(`图表已导出到导出中心：${res.data.name}`)
      }
    } catch (error: any) {
      showError(error, '图表导出失败')
    }
  }

  return { exportChartArtifact }
}
