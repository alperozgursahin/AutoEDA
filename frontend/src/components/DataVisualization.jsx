import { useState } from "react";
import { ChevronDown, BarChart3, ActivitySquare, Sigma, Layers3 } from "lucide-react";
import { BarChart, Bar, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, ComposedChart, Scatter } from "recharts";

function CorrelationMatrix({ correlations }) {
  const columns = correlations?.columns ?? [];
  const matrix = correlations?.matrix ?? [];
  if (!columns.length) return <p className="text-sm text-slate-500">No correlation data available.</p>;

  return (
    <div className="overflow-auto">
      <table className="min-w-full border-separate border-spacing-1 text-xs">
        <thead>
          <tr>
            <th className="p-2 text-left text-slate-500">Column</th>
            {columns.map((name) => (
              <th key={name} className="p-2 text-left text-slate-500">
                {name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {columns.map((rowName, rowIndex) => (
            <tr key={rowName}>
              <td className="rounded bg-slate-100 p-2 font-semibold text-slate-700">{rowName}</td>
              {matrix[rowIndex]?.map((value, colIndex) => {
                const alpha = Math.min(1, Math.abs(value));
                const bg = value >= 0 ? `rgba(59,130,246,${alpha})` : `rgba(239,68,68,${alpha})`;
                return (
                  <td key={`${rowName}-${columns[colIndex]}`} className="rounded p-2 text-white" style={{ backgroundColor: bg }}>
                    {Number(value).toFixed(2)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BoxPlotChart({ column, stats }) {
  const rangeData = [
    {
      name: column,
      q1: stats.q1,
      q3: stats.q3,
      iqr: Number((stats.q3 - stats.q1).toFixed(4)),
    },
  ];
  const medianData = [{ x: column, y: stats.median }];
  const outlierData = (stats.outliers || []).map((value) => ({ x: column, y: value }));

  return (
    <div className="h-52 w-full">
      <ResponsiveContainer>
        <ComposedChart data={rangeData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="iqr" stackId="a" fill="#93c5fd" />
          <Scatter data={medianData} dataKey="y" fill="#1d4ed8" />
          <Scatter data={outlierData} dataKey="y" fill="#ef4444" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function DataVisualization({ visualizationData, isLoading, error }) {
  const [openSection, setOpenSection] = useState("histograms");

  if (isLoading) {
    return (
      <section className="rounded-3xl border border-white/60 bg-white/70 p-6 shadow-lg backdrop-blur-xl">
        <div className="mb-4 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-blue-600" />
          <h2 className="text-lg font-semibold text-slate-800">Data Visualization Module</h2>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <div className="h-28 animate-pulse rounded-xl bg-slate-200" />
          <div className="h-28 animate-pulse rounded-xl bg-slate-200" />
          <div className="h-28 animate-pulse rounded-xl bg-slate-200" />
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-3xl border border-rose-200 bg-rose-50 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-rose-800">Data Visualization Module</h2>
        <p className="mt-2 text-sm text-rose-700">{error}</p>
      </section>
    );
  }

  if (!visualizationData) return null;

  const histogramEntries = Object.entries(visualizationData.histograms || {});
  const boxPlotEntries = Object.entries(visualizationData.box_plots || {});
  const categoricalEntries = Object.entries(visualizationData.categorical_counts || {});
  const sections = [
    { id: "histograms", title: "Histograms", icon: ActivitySquare, tone: "text-indigo-600" },
    { id: "box-plots", title: "Box Plot Statistics", icon: Layers3, tone: "text-emerald-600" },
    { id: "correlation", title: "Correlation Matrix", icon: Sigma, tone: "text-rose-600" },
    { id: "categorical", title: "Categorical Distributions", icon: BarChart3, tone: "text-blue-600" },
  ];

  return (
    <section className="rounded-3xl border border-white/60 bg-white/70 p-6 shadow-lg backdrop-blur-xl">
      <div className="mb-4 flex items-center gap-2">
        <BarChart3 className="h-5 w-5 text-blue-600" />
        <h2 className="text-lg font-semibold text-slate-800">Data Visualization Module</h2>
      </div>

      <div className="space-y-3">
        {sections.map((section) => {
          const Icon = section.icon;
          const isOpen = openSection === section.id;

          return (
            <article key={section.id} className="rounded-2xl border border-slate-200 bg-white/80">
              <button
                type="button"
                onClick={() => setOpenSection((prev) => (prev === section.id ? "" : section.id))}
                className="flex w-full items-center justify-between px-4 py-3 text-left"
              >
                <div className="flex items-center gap-2">
                  <Icon className={`h-4 w-4 ${section.tone}`} />
                  <h3 className="font-semibold text-slate-800">{section.title}</h3>
                </div>
                <ChevronDown className={`h-4 w-4 text-slate-500 transition ${isOpen ? "rotate-180" : ""}`} />
              </button>

              {isOpen && section.id === "histograms" && (
                <div className="grid gap-4 border-t border-slate-100 p-4 md:grid-cols-2">
                  {histogramEntries.length === 0 && <p className="text-sm text-slate-500">No histogram data available.</p>}
                  {histogramEntries.map(([column, bins]) => (
                    <div key={column} className="rounded-2xl border border-slate-200 bg-white p-4">
                      <p className="mb-2 text-sm font-semibold text-slate-700">{column}</p>
                      <div className="h-56 w-full">
                        <ResponsiveContainer>
                          <BarChart data={bins}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
                            <XAxis dataKey="bin_start" tick={{ fontSize: 10 }} />
                            <YAxis tick={{ fontSize: 10 }} />
                            <Tooltip />
                            <Bar dataKey="count" fill="#60a5fa" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {isOpen && section.id === "box-plots" && (
                <div className="grid gap-4 border-t border-slate-100 p-4 md:grid-cols-2">
                  {boxPlotEntries.length === 0 && <p className="text-sm text-slate-500">No box plot data available.</p>}
                  {boxPlotEntries.map(([column, stats]) => (
                    <div key={column} className="rounded-2xl border border-slate-200 bg-white p-4">
                      <p className="mb-2 text-sm font-semibold text-slate-700">{column}</p>
                      <p className="mb-2 text-xs text-slate-500">
                        Min: {stats.min} | Q1: {stats.q1} | Median: {stats.median} | Q3: {stats.q3} | Max: {stats.max}
                      </p>
                      <BoxPlotChart column={column} stats={stats} />
                    </div>
                  ))}
                </div>
              )}

              {isOpen && section.id === "correlation" && (
                <div className="border-t border-slate-100 p-4">
                  <CorrelationMatrix correlations={visualizationData.correlations} />
                </div>
              )}

              {isOpen && section.id === "categorical" && (
                <div className="grid gap-4 border-t border-slate-100 p-4 md:grid-cols-2">
                  {categoricalEntries.length === 0 && <p className="text-sm text-slate-500">No categorical distributions found.</p>}
                  {categoricalEntries.map(([column, values]) => (
                    <div key={column} className="rounded-2xl border border-slate-200 bg-white p-4">
                      <p className="mb-2 text-sm font-semibold text-slate-700">{column}</p>
                      <div className="h-56 w-full">
                        <ResponsiveContainer>
                          <BarChart data={values}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
                            <XAxis dataKey="value" tick={{ fontSize: 10 }} />
                            <YAxis tick={{ fontSize: 10 }} />
                            <Tooltip />
                            <Bar dataKey="count" fill="#2563eb" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

