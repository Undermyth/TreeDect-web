import { defineStore } from 'pinia'

export const useSegStore = defineStore('seg', {
    state: () => ({
        palette: [],
        showMask: true
    }),
    actions: {
        setPalette(value) {
            this.palette = value
        }
    }
})
