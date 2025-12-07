<template>
  <div class="log-container">
    <n-data-table :columns="tableColumns" :data="tableData" :flex-height="true" style="height: 100%"></n-data-table>
  </div>
</template>

<script setup>
import { useSegStore } from '@/stores/SegStore';
import { NButton, NDataTable } from 'naive-ui';
import { h, ref, watch } from 'vue';

const segStore = useSegStore();
const tableData = ref([]);
const tableColumns = [
  {
    title: "Class",
    key: "id",
    render(row) {
      return h(
        NButton,
        {
          strong: true,
          tertiary: true,
          size: 'small',
          color: segStore.colorMap[parseInt(row.id) + 1],
          onClick: () => onClickRow(row)
        },
        { default: () => `class ${row.id}` }
      )
    }
  },
  {
    title: "Importance Score",
    key: "score",
    sorter: (row1, row2) => row1.score - row2.score
  }
]

watch(() => segStore.clusterMap, (newClusterMap) => {
  console.log('Log.vue: clusterMap changed:');
  if (newClusterMap && newClusterMap.length > 0) {
    const count = Array(segStore.k).fill(0);
    const blockCount = Array(segStore.k).fill(0);
    const area = Array(segStore.k).fill(0);
    for (let i = 0; i < newClusterMap.length; i++) {
      if (newClusterMap[i] != -1) {
        const index = newClusterMap[i];
        count[index] += 1;
        blockCount[index] += segStore.blockCounts[i];
        area[index] += segStore.areas[i];
      }
    }
    const countScore = count.map(x => x / segStore.countTotal);
    const blockCountScore = blockCount.map(x => x / segStore.blockCountTotal);
    const areaScore = area.map(x => x / segStore.areasTotal);
    const averScore = countScore.map((x, i) => (x + blockCountScore[i] + areaScore[i]) / 3);
    
    tableData.value = averScore.map((score, index) => ({
      id: index.toString(),
      score: parseFloat(score.toFixed(3))
    }));
  }
}, { deep: true });

const onClickRow = (row) => {
    segStore.setHighlightCluster(parseInt(row.id));
}

</script>

<style scoped>
.log-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>