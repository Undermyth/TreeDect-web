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
    title: "Area (in pixels)",
    key: "area",
    sorter: (row1, row2) => row1.area - row2.area
  }
]

watch(() => segStore.areas, (newAreas) => {
    if (newAreas && newAreas.length > 0) {
      tableData.value = newAreas.map((area, index) => ({
        id: index.toString(),
        area: area
      }));
    }
});

const onClickRow = (row) => {
    segStore.setHighlightCluster(parseInt(row.id) + 1);
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