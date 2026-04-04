// frontend/src/workers/dataWorker.ts
self.onmessage = (e: MessageEvent) => {
  const { type, payload } = e.data;

  if (type === 'PROCESS_3D_BAR_DATA') {
    const { x_axis, y_axis } = payload;
    // 模拟大数据处理
    const data3D = x_axis.map((_: string, i: number) => [i, 0, y_axis[i]]);
    self.postMessage({ type: 'PROCESS_3D_BAR_DATA_RESULT', payload: data3D });
  } else if (type === 'FORMAT_NUMERIC_DESC') {
    const { numObj } = payload;
    const result = Object.keys(numObj).map(col => {
      return { col, ...numObj[col] };
    });
    self.postMessage({ type: 'FORMAT_NUMERIC_DESC_RESULT', payload: result });
  }
};
