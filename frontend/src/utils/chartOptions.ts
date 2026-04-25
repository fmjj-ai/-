/**
 * 通用 ECharts option 构造工厂。
 * 从各业务视图抽出的纯函数，不依赖任何组件状态。
 */

export interface WordFreqRow {
  label: string
  value: number
}

export interface CorrelationPayload {
  columns: string[]
  data: Array<[number, number, number | null]>
}

export interface AggregationPayload {
  x_axis: string[]
  y_axis: number[]
}

export const truncateLabel = (value: string, maxLength: number) =>
  value.length > maxLength ? `${value.slice(0, maxLength)}…` : value

export const calcZoomEnd = (total: number, visibleCount: number) => {
  if (total <= visibleCount) {
    return 100
  }
  return Math.max(20, Number(((visibleCount / total) * 100).toFixed(2)))
}

export const buildBarOptions = (
  labels: string[],
  values: number[],
  color: string,
  rotate = 30
) => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: labels, axisLabel: { rotate } },
  yAxis: { type: 'value' },
  series: [
    {
      type: 'bar',
      data: values,
      itemStyle: { color, borderRadius: [8, 8, 0, 0] },
    },
  ],
})

export const buildHistogramOptions = (labels: string[], counts: number[], color: string) =>
  buildBarOptions(labels, counts, color)

export const buildBoxplotOptions = (
  column: string,
  box: number[],
  outliers: number[],
  color: string,
  shape: string
) => ({
  tooltip: { trigger: 'item' },
  xAxis: { type: 'category', data: [column] },
  yAxis: { type: 'value' },
  series: [
    {
      name: '箱线图',
      type: 'boxplot',
      data: [box],
      itemStyle: { color, borderColor: color },
    },
    {
      name: '异常值',
      type: 'scatter',
      symbol: shape,
      itemStyle: { color },
      data: outliers.map((value) => [0, value]),
    },
  ],
})

export const buildWordFreqOptions = (rows: WordFreqRow[], color: string) =>
  buildBarOptions(
    rows.map((item) => item.label),
    rows.map((item) => item.value),
    color,
    28
  )

export const buildCorrelationHeatmapOptions = (payload: CorrelationPayload) => {
  const columnCount = payload.columns.length
  const showCellLabel = columnCount <= 18

  return {
    animation: false,
    tooltip: {
      confine: true,
      position: 'top',
      formatter: ({ data: item }: any) => {
        const xLabel = payload.columns[item[0]] ?? ''
        const yLabel = payload.columns[item[1]] ?? ''
        const value = item[2]
        return `${yLabel}<br/>${xLabel}<br/>相关系数：${value === null ? '-' : Number(value).toFixed(4)}`
      },
    },
    grid: { left: 240, right: 96, top: 24, bottom: 150 },
    xAxis: {
      type: 'category',
      data: payload.columns,
      splitArea: { show: true },
      axisLabel: {
        interval: 0,
        rotate: columnCount > 10 ? 40 : 20,
        formatter: (value: string) => truncateLabel(String(value), 12),
      },
    },
    yAxis: {
      type: 'category',
      data: payload.columns,
      splitArea: { show: true },
      axisLabel: {
        interval: 0,
        formatter: (value: string) => truncateLabel(String(value), 16),
      },
    },
    dataZoom: [
      {
        type: 'slider',
        xAxisIndex: 0,
        filterMode: 'none',
        bottom: 72,
        height: 14,
        start: 0,
        end: calcZoomEnd(columnCount, 10),
      },
      { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
      {
        type: 'slider',
        yAxisIndex: 0,
        filterMode: 'none',
        right: 20,
        width: 14,
        top: 24,
        bottom: 150,
        start: 0,
        end: calcZoomEnd(columnCount, 12),
      },
      { type: 'inside', yAxisIndex: 0, filterMode: 'none' },
    ],
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: 'vertical',
      right: 18,
      top: 'middle',
    },
    series: [
      {
        name: 'Correlation',
        type: 'heatmap',
        data: payload.data,
        progressive: 0,
        label: {
          show: showCellLabel,
          formatter: ({ data: item }: any) =>
            item[2] === null ? '-' : Number(item[2]).toFixed(2),
        },
        emphasis: {
          itemStyle: { borderColor: '#ffffff', borderWidth: 1 },
        },
      },
    ],
  }
}

export type GenericChartType = 'bar' | 'line' | 'pie' | 'bar3D'

export const buildGenericChartOptions = (
  payload: AggregationPayload,
  chartType: GenericChartType,
  color: string
) => {
  if (chartType === 'pie') {
    return {
      tooltip: { trigger: 'item' },
      legend: { orient: 'vertical', left: 'left' },
      series: [
        {
          type: 'pie',
          radius: '58%',
          data: payload.x_axis.map((item, index) => ({
            name: item,
            value: payload.y_axis[index],
          })),
        },
      ],
    }
  }

  if (chartType === 'bar3D') {
    return {
      tooltip: {},
      visualMap: {
        max: Math.max(...payload.y_axis, 1),
        inRange: { color: ['#e6f4ff', '#91caff', color] },
      },
      xAxis3D: { type: 'category', data: payload.x_axis },
      yAxis3D: { type: 'category', data: ['Series'] },
      zAxis3D: { type: 'value' },
      grid3D: { boxWidth: 180, boxDepth: 20, viewControl: { alpha: 12, beta: 18 } },
      series: [
        {
          type: 'bar3D',
          data: payload.y_axis.map((value, index) => [index, 0, value]),
          shading: 'lambert',
        },
      ],
    }
  }

  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: payload.x_axis },
    yAxis: { type: 'value' },
    series: [
      {
        type: chartType,
        smooth: chartType === 'line',
        data: payload.y_axis,
        itemStyle: { color },
        lineStyle: { color },
      },
    ],
  }
}

export const formatMetric = (value: any) => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(4) : '-'
}
