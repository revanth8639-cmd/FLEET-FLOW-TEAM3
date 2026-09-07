import { useMemo, useState } from "react";
import { FaFileExcel, FaFilePdf, FaChartBar } from "react-icons/fa";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";

const reportDefinitions = [
  { type: "fleet-utilization", name: "Fleet Utilization", description: "Vehicle status breakdown and utilization for the selected period.", roles: ["Admin", "FleetManager"] },
  { type: "fuel-consumption", name: "Fuel Consumption", description: "Fuel volume and spend by vehicle.", roles: ["Admin", "FleetManager"] },
  { type: "driver-performance", name: "Driver Performance", description: "Completed trips, on-time rate, and attendance.", roles: ["Admin", "FleetManager", "Driver"] },
  { type: "delivery-performance", name: "Delivery Performance", description: "On-time, delayed, and undelivered shipments.", roles: ["Admin", "FleetManager", "Dispatcher"] },
  { type: "maintenance", name: "Maintenance", description: "Maintenance costs, frequency, and upcoming or overdue work.", roles: ["Admin", "FleetManager"] },
];

const label = (value) => String(value).replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const display = (value) => {
  if (value == null) return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
};

const dateValue = (value) => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const currentPeriod = (period) => {
  const today = new Date();
  if (period === "week") {
    const start = new Date(today);
    const day = start.getDay() || 7;
    start.setDate(start.getDate() - day + 1);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    return { from: dateValue(start), to: dateValue(end) };
  }
  if (period === "month") {
    return {
      from: dateValue(new Date(today.getFullYear(), today.getMonth(), 1)),
      to: dateValue(new Date(today.getFullYear(), today.getMonth() + 1, 0)),
    };
  }
  return { from: "", to: "" };
};

const normalizeReport = (data, reportType, dateFrom, dateTo) => {
  const columns = Array.isArray(data?.columns) ? data.columns : [];
  const rows = Array.isArray(data?.rows) ? data.rows : [];
  if (columns.length) {
    return {
      report_type: data.report_type || reportType,
      title: data.title || "Report",
      date_from: data.date_from || dateFrom || null,
      date_to: data.date_to || dateTo || null,
      columns,
      rows,
      summary: data.summary && typeof data.summary === "object" ? data.summary : {},
      legacy: false,
    };
  }

  // Older backend processes returned only a count. Keep that response visible
  // instead of crashing the table while the server is being restarted.
  const countRows = Object.entries(data || {})
    .filter(([, value]) => typeof value === "number")
    .map(([metric, value]) => ({ metric, value }));
  return {
    report_type: reportType,
    title: `${label(reportType)} Report`,
    date_from: dateFrom || null,
    date_to: dateTo || null,
    columns: countRows.length ? ["metric", "value"] : [],
    rows: countRows,
    summary: data && typeof data === "object" ? data : {},
    legacy: true,
  };
};

async function errorMessage(requestError, fallback) {
  const data = requestError.response?.data;
  if (data instanceof Blob) {
    try {
      const parsed = JSON.parse(await data.text());
      return parsed.detail || fallback;
    } catch {
      return fallback;
    }
  }
  return data?.detail || fallback;
}

export default function Reports() {
  const { user } = useAuth();
  const availableReports = useMemo(() => reportDefinitions.filter((report) => report.roles.includes(user?.role)), [user?.role]);
  const [selectedType, setSelectedType] = useState("");
  const activeType = availableReports.some((item) => item.type === selectedType) ? selectedType : availableReports[0]?.type || "";
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [period, setPeriod] = useState("custom");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState("");
  const [error, setError] = useState("");

  async function loadReport(event) {
    event?.preventDefault();
    if (!activeType) return;
    setLoading(true);
    setError("");
    try {
      const response = await api.get(`/reports/${activeType}`, { params: { date_from: dateFrom || undefined, date_to: dateTo || undefined } });
      setReport(normalizeReport(response.data, activeType, dateFrom, dateTo));
    } catch (requestError) {
      setReport(null);
      setError(await errorMessage(requestError, "Unable to load report."));
    } finally {
      setLoading(false);
    }
  }

  async function download(format) {
    if (!activeType) return;
    setExporting(format);
    setError("");
    try {
      const response = await api.get(`/reports/${activeType}/export`, {
        params: { format, date_from: dateFrom || undefined, date_to: dateTo || undefined },
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${activeType}-report.${format === "pdf" ? "pdf" : "xlsx"}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(await errorMessage(requestError, "Unable to export report. Ensure the export dependencies are installed."));
    } finally {
      setExporting("");
    }
  }

  function changePeriod(value) {
    setPeriod(value);
    if (value !== "custom") {
      const range = currentPeriod(value);
      setDateFrom(range.from);
      setDateTo(range.to);
    }
  }

  if (!availableReports.length) {
    return <main className="p-8"><h1 className="text-3xl font-bold text-slate-900">Reports & Export</h1><p className="mt-3 text-slate-600">Your role does not have access to report generation.</p></main>;
  }

  const selected = reportDefinitions.find((item) => item.type === activeType);
  return <main className="min-h-screen bg-slate-50 p-5 md:p-8">
    <div className="mb-6"><h1 className="text-3xl font-bold text-slate-900">Reports & Export</h1><p className="mt-1 text-slate-500">Generate a role-scoped report preview before downloading.</p></div>
    {error && <div className="mb-5 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-red-700">{error}</div>}
    <section className="mb-6 rounded-lg bg-white p-5 shadow-sm">
      <form onSubmit={loadReport} className="grid gap-4 md:grid-cols-[minmax(220px,1fr)_170px_180px_180px_auto] md:items-end">
        <label className="text-sm font-semibold text-slate-700">Report type<select value={activeType} onChange={(event) => { setSelectedType(event.target.value); setReport(null); }} className="mt-1 block w-full rounded-md border border-slate-200 px-3 py-2.5 font-normal"><option value="" disabled>Select a report</option>{availableReports.map((item) => <option key={item.type} value={item.type}>{item.name}</option>)}</select></label>
        <label className="text-sm font-semibold text-slate-700">Period<select value={period} onChange={(event) => changePeriod(event.target.value)} className="mt-1 block w-full rounded-md border border-slate-200 px-3 py-2.5 font-normal"><option value="week">This week</option><option value="month">This month</option><option value="custom">Custom dates</option></select></label>
        <label className="text-sm font-semibold text-slate-700">From<input type="date" value={dateFrom} disabled={period !== "custom"} onChange={(event) => { setPeriod("custom"); setDateFrom(event.target.value); }} className="mt-1 block w-full rounded-md border border-slate-200 px-3 py-2.5 font-normal disabled:bg-slate-100" /></label>
        <label className="text-sm font-semibold text-slate-700">To<input type="date" value={dateTo} disabled={period !== "custom"} onChange={(event) => { setPeriod("custom"); setDateTo(event.target.value); }} className="mt-1 block w-full rounded-md border border-slate-200 px-3 py-2.5 font-normal disabled:bg-slate-100" /></label>
        <button disabled={loading} className="inline-flex items-center justify-center gap-2 rounded-md bg-indigo-600 px-5 py-2.5 font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"><FaChartBar />{loading ? "Generating..." : "Generate"}</button>
      </form>
      {selected && <p className="mt-3 text-sm text-slate-500">{selected.description}</p>}
    </section>
    {report && <section className="rounded-lg bg-white p-5 shadow-sm">
      <div className="mb-5 flex flex-col gap-3 border-b border-slate-100 pb-4 md:flex-row md:items-start md:justify-between"><div><h2 className="text-xl font-bold text-slate-900">{report.title}</h2><p className="text-sm text-slate-500">{report.date_from || "All dates"} to {report.date_to || "Present"}</p></div><div className="flex gap-2"><button onClick={() => void download("pdf")} disabled={Boolean(exporting)} className="inline-flex items-center gap-2 rounded-md bg-rose-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"><FaFilePdf />{exporting === "pdf" ? "Preparing..." : "PDF"}</button><button onClick={() => void download("xlsx")} disabled={Boolean(exporting)} className="inline-flex items-center gap-2 rounded-md bg-emerald-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"><FaFileExcel />{exporting === "xlsx" ? "Preparing..." : "Excel"}</button></div></div>
      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{Object.entries(report.summary || {}).filter(([, value]) => typeof value !== "object").map(([key, value]) => <div key={key} className="rounded-md border border-slate-100 bg-slate-50 p-3"><p className="text-xs font-semibold uppercase text-slate-500">{label(key)}</p><p className="mt-1 text-xl font-bold text-slate-900">{display(value)}</p></div>)}</div>
      {report.legacy && <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">This server returned a legacy count-only response. Restart the backend to show the full assigned report fields.</div>}
      {report.columns.length ? <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-sm"><thead className="border-y border-slate-100 bg-slate-50 text-left text-xs uppercase text-slate-500"><tr>{report.columns.map((column) => <th key={column} className="px-3 py-3">{label(column)}</th>)}</tr></thead><tbody>{report.rows.map((row, index) => <tr key={index} className="border-b border-slate-100 text-slate-700">{report.columns.map((column) => <td key={column} className="px-3 py-3">{display(row[column])}</td>)}</tr>)}{!report.rows.length && <tr><td colSpan={report.columns.length} className="px-3 py-8 text-center text-slate-500">No records match this date range.</td></tr>}</tbody></table></div> : <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-5 text-sm text-amber-800">The report response was empty. Check the backend connection and generate again.</div>}
    </section>}
    {!report && !loading && <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">Choose a report and date range, then select Generate to preview it.</div>}
  </main>;
}
