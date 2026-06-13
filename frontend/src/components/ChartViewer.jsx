/**
 * ChartViewer.jsx – wrapper nhẹ.
 * Plotly (~3MB) được lazy-load chỉ khi component này mount lần đầu.
 * Trong khi đợi hiển thị skeleton animation thay vì hộp trống.
 */
import React, { Suspense, lazy } from 'react';
import './ChartViewer.css';

// Lazy import – Vite sẽ tách PlotlyChart thành chunk riêng
const PlotlyChart = lazy(() => import('./PlotlyChart'));

// ---------------------------------------------------------------------------
// Skeleton – hiển thị trong khi Plotly đang tải
// ---------------------------------------------------------------------------
const ChartSkeleton = () => (
  <div className="chart-skeleton" aria-label="Đang tải biểu đồ...">
    <div className="chart-skeleton-shimmer" />
    <div className="chart-skeleton-bars">
      {[65, 90, 45, 78, 55, 82, 38, 70, 60, 88].map((h, i) => (
        <div
          key={i}
          className="chart-skeleton-bar"
          style={{ height: `${h}%`, animationDelay: `${i * 0.07}s` }}
        />
      ))}
    </div>
    <div className="chart-skeleton-label">Đang tải biểu đồ…</div>
  </div>
);

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------
const ChartViewer = ({ chartData }) => {
  if (!chartData || chartData.type !== 'plotly') return null;

  return (
    <div className="chart-container">
      <Suspense fallback={<ChartSkeleton />}>
        <PlotlyChart chartData={chartData} />
      </Suspense>
    </div>
  );
};

export default ChartViewer;
