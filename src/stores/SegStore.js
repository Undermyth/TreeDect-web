import { defineStore } from 'pinia'

export const useSegStore = defineStore('seg', {
    state: () => ({
        palette: [],
        showMask: true,
        showIndex: true,
        k: 6,
        segRatio: 2,
        colorMap: null,
        highlightCluster: -1,
        clusterMap: [],
        areas: [],
        blockCounts: [],
        countTotal: 0,
        blockCountTotal: 0,
        areasTotal: 0,
    }),
    actions: {
        setPalette(value) {
            this.palette = value
        },
        setColorMap(value) {
            this.colorMap = value
        },
        setHighlightCluster(value) {
            this.highlightCluster = value
        },
        setClusterMap(value) {
            this.clusterMap = value
        },
        updateClusterMap(index, value) {
            if (index >= 0 && index < this.clusterMap.length) {
                this.clusterMap.splice(index, 1, value);
            }
        },
        setAreas(value) {
            this.areas = [...value];
        },
        setBlockCounts(value) {
            this.blockCounts = value
        },
    }
})
