import { defineStore } from 'pinia'

export const useSegStore = defineStore('seg', {
    state: () => ({
        palette: []
    }),
    actions: {
        setPalette(value) {
            this.palette = value
        }
    }
})
