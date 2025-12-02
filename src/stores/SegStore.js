import { defineStore } from 'pinia'

export const useSegStore = defineStore('seg', {
    state: () => ({
        palette: [],
        showMask: true,
        showIndex: true,
        k: 6,
        colorMap: null,
        areas: [],
        highlightCluster: -1
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
        },
        setHighlightCluster(value) {
            this.highlightCluster = value
        }
    }
})
