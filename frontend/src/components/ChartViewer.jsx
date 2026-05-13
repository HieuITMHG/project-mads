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
    return field; // Không phải binary, trả nguyên
  }

  try {
    // Base64 → Uint8Array
    const binaryStr = atob(field.bdata);
    const bytes = new Uint8Array(binaryStr.length);
    for (let i = 0; i < binaryStr.length; i++) {
      bytes[i] = binaryStr.charCodeAt(i);
    }

    const view = new DataView(bytes.buffer);
    const result = [];
    const LE = true; // little-endian (numpy default)

    if (field.dtype === 'f8') {        // float64, 8 bytes
      for (let i = 0; i < bytes.length; i += 8) result.push(view.getFloat64(i, LE));
    } else if (field.dtype === 'f4') { // float32, 4 bytes
      for (let i = 0; i < bytes.length; i += 4) result.push(view.getFloat32(i, LE));
    } else if (field.dtype === 'i4') { // int32, 4 bytes
      for (let i = 0; i < bytes.length; i += 4) result.push(view.getInt32(i, LE));
    } else if (field.dtype === 'i2') { // int16, 2 bytes
      for (let i = 0; i < bytes.length; i += 2) result.push(view.getInt16(i, LE));
    } else {
      console.warn('[ChartViewer] Unknown dtype:', field.dtype);
      return field;
    }

    return result;
  } catch (e) {
    console.error('[ChartViewer] Failed to decode binary field:', e, field);
    return field;
  }
};

/** Giải mã toàn bộ một trace: x, y, z, ... có thể là binary */
const decodeTrace = (trace) => {
  if (!trace || typeof trace !== 'object') return trace;
  const decoded = { ...trace };
  for (const key of ['x', 'y', 'z', 'open', 'high', 'low', 'close', 'values', 'labels']) {
    if (decoded[key] !== undefined) {
      decoded[key] = decodeBinaryField(decoded[key]);
    }
  }
  return decoded;
};


const ChartViewer = ({ chartData }) => {
  // [DEBUG] Log mỗi lần ChartViewer được gọi
  console.log('[ChartViewer] received chartData:', chartData);

  if (!chartData || chartData.type !== 'plotly') {
    console.warn('[ChartViewer] Returning null — chartData invalid or type not plotly:', chartData);
    return null;
  }

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
        const decoded = decodeTrace(item);
        console.log('[ChartViewer] decoded trace — x:', decoded.x, 'y:', decoded.y);
        validData.push(decoded);
      }
    });

    console.log('[ChartViewer] Final validData:', validData);
    return { validData, extractedLayout };
  }, [chartData]);

  const layout = useMemo(() => {
    return {
      ...extractedLayout,
      autosize: true,
      margin: { l: 50, r: 30, t: 50, b: 50 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: {
        family: 'inherit',
        color: 'var(--text-color, #e0e0e0)'
      }
    };
  }, [chartData.layout]);

  const config = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
  };

  console.log('[ChartViewer] Rendering <Plot> with validData length:', validData.length);

  return (
    <div
      className="chart-container"
      style={{
        width: '100%',
        boxSizing: 'border-box',
        height: '420px',
        margin: '1.5rem 0',
        position: 'relative',
        borderRadius: '8px',
        overflow: 'hidden',
      }}
    >
      <Plot
        data={validData}
        layout={layout}
        config={config}
        useResizeHandler={true}
        style={{ width: '100%', height: '100%' }}
      />
    </div>
  );
};

export default ChartViewer;
