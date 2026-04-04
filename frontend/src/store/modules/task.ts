import { defineStore } from 'pinia'
import request from '@/utils/request'

export const useTaskStore = defineStore('task', {
  state: () => ({
    tasks: [] as any[],
    eventSource: null as EventSource | null,
    unreadCount: 0,
    showTaskCenter: false
  }),
  actions: {
    async fetchTasks(projectId: string) {
      try {
        const res: any = await request.get('/tasks/', { params: { project_id: projectId } })
        if (res.success) {
          this.tasks = res.data
        }
      } catch (e) {
        console.error('Failed to fetch tasks', e)
      }
    },
    async deleteTask(taskId: string) {
      try {
        const res: any = await request.delete(`/tasks/${taskId}`)
        if (res.success) {
          this.tasks = this.tasks.filter(t => t.id !== taskId)
        }
      } catch (e) {
        console.error('Failed to delete task', e)
      }
    },
    connectSSE() {
      if (this.eventSource) return

      // Use absolute path with Vite proxy
      const url = import.meta.env.VITE_API_BASE_URL 
        ? `${import.meta.env.VITE_API_BASE_URL}/tasks/stream/events`
        : '/api/v1/tasks/stream/events'
        
      this.eventSource = new EventSource(url)
      
      this.eventSource.onmessage = (event) => {
        if (event.data === 'ping') return
        
        try {
          const data = JSON.parse(event.data)
          // `data` 可能是任务更新，也可能是新任务
          const index = this.tasks.findIndex(t => t.id === data.task_id)
          if (index !== -1) {
            this.tasks[index].status = data.status
            this.tasks[index].progress = data.progress
            if (data.result) this.tasks[index].result = data.result
            if (data.error_msg) this.tasks[index].error_msg = data.error_msg
          } else {
            // New task
            this.tasks.unshift({
              id: data.task_id,
              status: data.status,
              progress: data.progress,
              result: data.result,
              error_msg: data.error_msg,
              name: data.name || '未命名任务',
              type: data.type || 'unknown',
              created_at: new Date().toISOString()
            })
          }
          if (!this.showTaskCenter) {
            this.unreadCount++
          }
        } catch (e) {
          console.error('SSE parse error', e)
        }
      }
      
      this.eventSource.onerror = (e) => {
        console.error('SSE Error', e)
        this.disconnectSSE()
        // Retry logic after 5 seconds
        setTimeout(() => this.connectSSE(), 5000)
      }
    },
    disconnectSSE() {
      if (this.eventSource) {
        this.eventSource.close()
        this.eventSource = null
      }
    },
    toggleTaskCenter() {
      this.showTaskCenter = !this.showTaskCenter
      if (this.showTaskCenter) {
        this.unreadCount = 0
      }
    }
  }
})
