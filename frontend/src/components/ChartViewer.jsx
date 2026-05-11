import React, { useMemo } from 'react';
import Plotly from 'plotly.js-dist-min';
import factory from 'react-plotly.js/factory';

const createPlotlyComponent = factory.default || factory;
const Plot = createPlotlyComponent(Plotly);

const ChartViewer = ({ chartData }) => {
  if (!chartData || chartData.type !== 'plotly') {
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
        validData.push(item);
      }
    });

    return { validData, extractedLayout };
  }, [chartData]);

  const layout = useMemo(() => {
    return {
      ...extractedLayout,
      autosize: true, // Cho phép Plotly tự co giãn
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

  return (
    // THAY ĐỔI 1: Ép cứng min-height và cho phép flex grow
    <div
      className="chart-container"
      style={{
        width: '100%',
        minHeight: '400px', // Đảm bảo luôn có độ cao
        height: '400px',    // Ép chiều cao cố định để test (có thể bỏ đi sau này)
        margin: '1.5rem 0',
        position: 'relative', // Giúp Plotly đo đạc kích thước dễ hơn
        border: '1px dashed #555', // Viền mờ để bác nhìn thấy KHUNG của đồ thị (xóa đi sau khi debug xong)
        borderRadius: '8px'
      }}
    >
      <Plot
        data={validData}
        layout={layout}
        config={config}
        // THAY ĐỔI 2: Ép useResizeHandler để Plotly vẽ lại khi khung thay đổi
        useResizeHandler={true}
        style={{ width: '100%', height: '100%' }}
      />
    </div>
  );
};

export default ChartViewer;
