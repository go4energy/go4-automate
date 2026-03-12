<script setup>
import { computed } from 'vue'
import VueApexCharts from 'vue3-apexcharts'

const props = defineProps({
  data: { type: Array, default: () => [] }
})

const chartOptions = computed(() => ({
  chart: {
    type: 'line',
    height: 350,
    toolbar: { show: true },
    zoom: { enabled: true }
  },
  colors: ['#00A67E', '#3B82F6', '#F59E0B'],
  stroke: {
    width: [3, 3, 2],
    curve: 'smooth',
    dashArray: [0, 0, 5]
  },
  xaxis: {
    categories: props.data.map((d) => d.date),
    labels: {
      style: { fontSize: '11px' },
      rotate: -45,
      rotateAlways: props.data.length > 14
    }
  },
  yaxis: [
    {
      title: { text: 'Ausgaben / CPL' },
      labels: {
        formatter: (val) => `${Number(val).toFixed(2)}`
      }
    },
    {
      opposite: true,
      title: { text: 'Leads' },
      labels: {
        formatter: (val) => Math.round(val).toString()
      }
    }
  ],
  legend: {
    position: 'top',
    horizontalAlign: 'left'
  },
  tooltip: {
    shared: true,
    intersect: false,
    y: {
      formatter: (val, { seriesIndex }) => {
        if (seriesIndex === 1) return Math.round(val).toString()
        return `${Number(val).toFixed(2)}`
      }
    }
  }
}))

const chartSeries = computed(() => [
  {
    name: 'Ausgaben',
    type: 'line',
    data: props.data.map((d) => Number(d.spend || 0))
  },
  {
    name: 'Leads',
    type: 'column',
    data: props.data.map((d) => d.leads || 0)
  },
  {
    name: 'CPL',
    type: 'line',
    data: props.data.map((d) => Number(d.cpl || 0))
  }
])
</script>

<template>
  <div class="rounded-lg bg-white p-6 shadow-sm">
    <h3 class="mb-4 text-sm font-medium text-go4-muted">
      Performance (letzten 30 Tage)
    </h3>
    <div
      v-if="props.data.length === 0"
      class="flex h-64 items-center justify-center text-go4-muted"
    >
      Keine Performance-Daten vorhanden
    </div>
    <VueApexCharts
      v-else
      type="line"
      height="350"
      :options="chartOptions"
      :series="chartSeries"
    />
  </div>
</template>
