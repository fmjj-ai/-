import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { getErrorDetail } from '@/utils/request'

/**
 * 通用的"加载 + 错误提示"封装。
 * - `run(task, fallback)`：以 loading 状态运行一个异步任务，失败时统一使用 getErrorDetail 弹出错误。
 * - `showError(err, fallback)`：与原视图中 showPageError 行为一致，单独暴露以便在非 loading 路径也能复用。
 */
export function useAsyncAction() {
  const loading = ref(false)

  const showError = (error: any, fallback: string) => {
    message.error(getErrorDetail(error, fallback))
  }

  const run = async (task: () => Promise<void>, fallback: string) => {
    loading.value = true
    try {
      await task()
    } catch (error: any) {
      showError(error, fallback)
    } finally {
      loading.value = false
    }
  }

  return { loading, run, showError }
}
