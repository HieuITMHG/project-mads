/**
 * PlotlyChart.jsx – phần nặng chứa Plotly, được lazy-load khi cần.
 * KHÔNG import file này trực tiếp — dùng qua ChartViewer.jsx (React.lazy).
 */
import React, { useMemo } from 'react';
import Plotly from 'plotly.js-dist-min';
import factory from 'react-plotly.js/factory';

const createPlotlyComponent = factory.default || factory;
const Plot = createPlotlyComponent(Plotly);

/**
 * Giải mã trường binary của Plotly Python (bdata + dtype) thành mảng số thông thường.
 * Plotly Python đôi khi serialize numpy arrays thành base64 binary thay vì JSON array.
 */
const decodeBinaryField = (field) => {
  if (!field || typeof field !== 'object' || !field.bdata || !field.dtype) {
    return field;
  }
  try {
    const binaryStr = atob(field.bdata);
    const bytes = new Uint8Array(binaryStr.length);
    for (let i = 0; i < binaryStr.length; i++) bytes[i] = binaryStr.charCodeAt(i);
    const view = new DataView(bytes.buffer);
    const result = [];
    const LE = true;
    if (field.dtype === 'f8') for (let i = 0; i < bytes.length; i += 8) result.push(view.getFloat64(i, LE));
    else if (field.dtype === 'f4') for (let i = 0; i < bytes.length; i += 4) result.push(view.getFloat32(i, LE));
    else if (field.dtype === 'i4') for (let i = 0; i < bytes.length; i += 4) result.push(view.getInt32(i, LE));
    else if (field.dtype === 'i2') for (let i = 0; i < bytes.length; i += 2) result.push(view.getInt16(i, LE));
    else { console.warn('[PlotlyChart] Unknown dtype:', field.dtype); return field; }
    return result;
  } catch (e) {
    console.error('[PlotlyChart] Failed to decode binary field:', e);
    return field;
  }
};

const deepDecodeBinary = (obj) => {
  if (!obj || typeof obj !== 'object') return obj;
  if (Array.isArray(obj)) return obj.map(deepDecodeBinary);
  if (obj.bdata && obj.dtype) return decodeBinaryField(obj);

  const newObj = {};
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      newObj[key] = deepDecodeBinary(obj[key]);
    }
  }
  return newObj;
};

const PlotlyChart = ({ chartData }) => {
  const { validData, extractedLayout } = useMemo(() => {
    let validData = [];
    let extractedLayout = { ...(chartData.layout || {}) };
    const dataArray = Array.isArray(chartData.data) ? chartData.data : [];
    dataArray.forEach(item => {
      if (item && typeof item === 'object' && item.type === 'layout') {
        if (Object.keys(extractedLayout).length === 0) {
          const { type, ...rest } = item;
          extractedLayout = rest;
        }
      } else {
        validData.push(deepDecodeBinary(item));
      }
    });
    return { validData, extractedLayout };
  }, [chartData]);

  const layout = useMemo(() => {
    const hasPie = validData.some(trace => trace.type === 'pie' || trace.type === 'sunburst');
    const layoutConfig = {
      ...extractedLayout,
      autosize: true,
      margin: { l: 50, r: 30, t: 50, b: 50 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { family: 'Inter, sans-serif', color: '#e2e8f0' },
    };

    if (!hasPie) {
      layoutConfig.xaxis = { gridcolor: 'rgba(255,255,255,0.06)', zerolinecolor: 'rgba(255,255,255,0.1)', ...extractedLayout.xaxis };
      layoutConfig.yaxis = { gridcolor: 'rgba(255,255,255,0.06)', zerolinecolor: 'rgba(255,255,255,0.1)', ...extractedLayout.yaxis };
    }

    return layoutConfig;
  }, [extractedLayout, validData]);
  const config = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['toImage', 'sendDataToCloud'],
  };

  return (
    <Plot
      data={validData}
      layout={layout}
      config={config}
      useResizeHandler
      style={{ width: '100%', height: '100%' }}
    />
  );
};

export default PlotlyChart;
