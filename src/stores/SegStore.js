import { defineStore } from 'pinia'

export const useSegStore = defineStore('seg', {
    state: () => ({
        palette: [],
        showMask: true,
        k: 6,
        colorMap: null,
        areas: []
    }),
    actions: {
        setPalette(value) {
            this.palette = value
        },
        setColorMap(value) {
            this.colorMap = value
        },
        setAreas(value) {
            this.areas = [...value];
        }
    }
})
