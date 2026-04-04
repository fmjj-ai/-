import { defineStore } from 'pinia'

export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProjectId: null as string | null,
    projects: [] as any[]
  }),
  actions: {
    setCurrentProject(id: string) {
      this.currentProjectId = id
    }
  }
})
