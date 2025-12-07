<template>
  <div class="log-container">
    <n-data-table :columns="tableColumns" :data="tableData" :flex-height="true" style="height: 100%"></n-data-table>
    <div class="export-button-container">
      <n-button @click="exportToCSV" type="primary" size="small">导出 CSV</n-button>
    </div>
  </div>
</template>

<script setup>
import { useSegStore } from '@/stores/SegStore';
import { NButton, NDataTable } from 'naive-ui';
import { h, ref, watch } from 'vue';

const segStore = useSegStore();
const tableData = ref([]);
const exportData = ref([]); // 用于存储导出数据
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
    
    // 准备导出数据
    const exportRows = [];
    for (let i = 0; i < segStore.k; i++) {
      exportRows.push({
        class: `class ${i}`,
        averScore: parseFloat(averScore[i].toFixed(3)),
        count: count[i],
        countScore: parseFloat(countScore[i].toFixed(3)),
        blockCount: blockCount[i],
        blockCountScore: parseFloat(blockCountScore[i].toFixed(3)),
        area: parseFloat(area[i].toFixed(3)),
        areaScore: parseFloat(areaScore[i].toFixed(3))
      });
    }
    // 按 averScore 从高到低排序
    exportRows.sort((a, b) => b.averScore - a.averScore);
    exportData.value = exportRows;
  }
}, { deep: true });

const onClickRow = (row) => {
    segStore.setHighlightCluster(parseInt(row.id));
}

const exportToCSV = () => {
  if (exportData.value.length === 0) {
    console.warn('No data to export');
    return;
  }
  
  // CSV 列标题
  const headers = ['Class', '重要值', '多度', '相对多度', '频度', '相对频度', '显著度', '相对显著度'];
  
  // 构建 CSV 内容
  let csvContent = headers.join(',') + '\n';
  
  exportData.value.forEach(row => {
    const csvRow = [
      row.class,
      row.averScore,
      row.count,
      row.countScore,
      row.blockCount,
      row.blockCountScore,
      row.area,
      row.areaScore
    ].map(value => {
      // 处理包含逗号、引号或换行符的值
      if (typeof value === 'string' && (value.includes(',') || value.includes('"') || value.includes('\n'))) {
        return '"' + value.replace(/"/g, '""') + '"';
      }
      return value;
    }).join(',');
    csvContent += csvRow + '\n';
  });
  
  // 创建并下载文件
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', 'cluster_analysis.csv');
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

</script>

<style scoped>
.log-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.export-button-container {
  margin-bottom: 10px;
  display: flex;
  justify-content: flex-end;
}
</style>