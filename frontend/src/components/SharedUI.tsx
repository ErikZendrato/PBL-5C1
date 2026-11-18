import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  CheckCircle,
  HeartHandshake,
  Info,
  MinusCircle,
  Search,
} from "lucide-react";

export type Status = "Baik" | "Cukup" | "Perlu Perhatian";

export function StatusBadge({ status, large = false }: { status: Status; large?: boolean }) {
  const Icon = status === "Baik" ? CheckCircle : status === "Cukup" ? MinusCircle : HeartHandshake;
  return (
    <span className={`status-badge status-${statusClass(status)}${large ? " status-large" : ""}`}>
      <Icon size={large ? 22 : 17} aria-hidden="true" />
      {status}
    </span>
  );
}

function statusClass(status: Status) {
  return status === "Baik" ? "baik" : status === "Cukup" ? "cukup" : "perhatian";
}

export function StatCard({
  icon,
  label,
  value,
  delta,
}: {
  icon: ReactNode;
  label: ReactNode;
  value: string | number;
  delta?: string;
}) {
  const [animatedValue, setAnimatedValue] = useState(0);
  useEffect(() => {
    if (typeof value !== "number") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setAnimatedValue(value);
      return;
    }

    let frame = 0;
    const startedAt = performance.now();
    const animate = (now: number) => {
      const progress = Math.min((now - startedAt) / 450, 1);
      setAnimatedValue(Math.round(value * progress));
      if (progress < 1) frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [value]);

  return (
    <article className="stat-card">
      <span className="stat-icon" aria-hidden="true">{icon}</span>
      <span className="stat-label">{label}</span>
      <strong aria-label={String(value)}>{typeof value === "number" ? animatedValue : value}</strong>
      {delta && <small>{delta}</small>}
    </article>
  );
}

export function PredictionCard({
  value,
  lower,
  upper,
  status,
  studentFriendly = false,
}: {
  value: number;
  lower: number;
  upper: number;
  status: Status;
  studentFriendly?: boolean;
}) {
  return (
    <article className="prediction-card">
      <p className="eyebrow">{studentFriendly ? "GAMBARAN SEMESTER DEPAN" : "PERKIRAAN NILAI"}</p>
      <strong className="predicted-value">{value.toFixed(2)}</strong>
      <p className="prediction-range">Kisaran {lower.toFixed(2)}–{upper.toFixed(2)}</p>
      <StatusBadge status={status} />
      <p className="prediction-explainer">
        {studentFriendly
          ? "Ini perkiraan untuk membantu kamu menyiapkan langkah berikutnya. Hasil belajar bisa berubah."
          : "Kisaran ini berdasarkan hasil uji model, bukan jaminan nilai akhir."}
      </p>
    </article>
  );
}

export function InfoTooltip({ label, text }: { label: string; text: string }) {
  return (
    <span className="info-tooltip">
      <button type="button" aria-label={`Penjelasan: ${label}`} title={text}>
        <Info size={16} aria-hidden="true" />
      </button>
      <span role="tooltip">{text}</span>
    </span>
  );
}

export type DataColumn<T> = {
  key: string;
  label: string;
  value: (row: T) => string | number;
  render?: (row: T) => ReactNode;
};

export function DataTable<T>({
  rows,
  columns,
  rowId,
  onRowClick,
  emptyTitle = "Belum ada data",
  emptyText = "Data yang sesuai akan muncul di sini.",
}: {
  rows: T[];
  columns: DataColumn<T>[];
  rowId: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyTitle?: string;
  emptyText?: string;
}) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState(columns[0]?.key ?? "");
  const [ascending, setAscending] = useState(true);
  const [page, setPage] = useState(0);
  const pageSize = 8;
  useEffect(() => {
    const handleSearch = (event: Event) => {
      setQuery((event as CustomEvent<string>).detail);
      setPage(0);
    };
    window.addEventListener("app-search", handleSearch);
    return () => window.removeEventListener("app-search", handleSearch);
  }, []);
  const visibleRows = useMemo(() => {
    const filtered = rows.filter((row) =>
      columns.some((column) =>
        String(column.value(row)).toLocaleLowerCase("id").includes(query.toLocaleLowerCase("id")),
      ),
    );
    const sortColumn = columns.find((column) => column.key === sortKey);
    if (sortColumn) {
      filtered.sort((left, right) => {
        const a = sortColumn.value(left);
        const b = sortColumn.value(right);
        const compared = typeof a === "number" && typeof b === "number"
          ? a - b
          : String(a).localeCompare(String(b), "id");
        return ascending ? compared : -compared;
      });
    }
    return filtered;
  }, [ascending, columns, query, rows, sortKey]);
  const pageCount = Math.max(1, Math.ceil(visibleRows.length / pageSize));
  const safePage = Math.min(page, pageCount - 1);
  const pagedRows = visibleRows.slice(safePage * pageSize, (safePage + 1) * pageSize);

  if (!rows.length) return <EmptyState title={emptyTitle} text={emptyText} />;
  return (
    <div className="data-table">
      <label className="table-search">
        <Search size={18} aria-hidden="true" />
        <input
          type="search"
          value={query}
          aria-label="Cari dalam tabel"
          placeholder="Cari data..."
          onChange={(event) => {
            setQuery(event.target.value);
            setPage(0);
          }}
        />
      </label>
      <div className="table-wrap">
        <table>
          <thead><tr>{columns.map((column) => (
            <th key={column.key}>
              <button
                type="button"
                className="table-sort"
                onClick={() => {
                  if (sortKey === column.key) setAscending((value) => !value);
                  else {
                    setSortKey(column.key);
                    setAscending(true);
                  }
                }}
                aria-label={`Urutkan berdasarkan ${column.label}`}
              >
                {column.label}{sortKey === column.key ? (ascending ? " ↑" : " ↓") : ""}
              </button>
            </th>
          ))}</tr></thead>
          <tbody>{pagedRows.map((row) => (
            <tr
              key={rowId(row)}
              className={onRowClick ? "clickable-row" : ""}
              onClick={() => onRowClick?.(row)}
              onKeyDown={(event) => {
                if (onRowClick && (event.key === "Enter" || event.key === " ")) {
                  event.preventDefault();
                  onRowClick(row);
                }
              }}
              tabIndex={onRowClick ? 0 : undefined}
            >
              {columns.map((column) => (
                <td key={column.key}>{column.render ? column.render(row) : column.value(row)}</td>
              ))}
            </tr>
          ))}</tbody>
        </table>
        {!pagedRows.length && <EmptyState title="Tidak ada hasil" text="Coba kata pencarian yang berbeda." />}
      </div>
      <div className="table-pagination">
        <span>{visibleRows.length ? `${safePage * pageSize + 1}–${Math.min((safePage + 1) * pageSize, visibleRows.length)} dari ${visibleRows.length}` : "0 data"}</span>
        <div>
          <button type="button" className="secondary-button" disabled={safePage === 0} onClick={() => setPage((value) => Math.max(0, value - 1))}>Sebelumnya</button>
          <button type="button" className="secondary-button" disabled={safePage >= pageCount - 1} onClick={() => setPage((value) => Math.min(pageCount - 1, value + 1))}>Berikutnya</button>
        </div>
      </div>
    </div>
  );
}

export function Skeleton({ rows = 3 }: { rows?: number }) {
  return <div className="skeleton-list" aria-label="Sedang memuat" aria-busy="true">{Array.from({ length: rows }, (_, index) => <span key={index} />)}</div>;
}

export function EmptyState({ title, text, action }: { title: string; text: string; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <svg viewBox="0 0 120 90" role="img" aria-label="Ilustrasi data kosong">
        <rect x="20" y="12" width="80" height="62" rx="12" fill="none" stroke="currentColor" strokeWidth="3" />
        <path d="M36 55 49 42l10 8 19-22" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="78" cy="28" r="4" fill="currentColor" />
      </svg>
      <strong>{title}</strong>
      <p>{text}</p>
      {action}
    </div>
  );
}

export function ConfirmDialog({
  title,
  message,
  confirmLabel = "Hapus",
  onConfirm,
  onCancel,
}: {
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onCancel()}>
      <section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-message">
        <h2 id="confirm-title">{title}</h2>
        <p id="confirm-message">{message}</p>
        <div className="dialog-actions">
          <button className="secondary-button" onClick={onCancel}>Batal</button>
          <button className="danger-button" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </section>
    </div>
  );
}

export function Toast({ message, kind = "success", onClose }: { message: string; kind?: "success" | "error"; onClose: () => void }) {
  if (!message) return null;
  return (
    <div className={`toast toast-${kind}`} role={kind === "error" ? "alert" : "status"}>
      <span>{message}</span>
      <button type="button" aria-label="Tutup notifikasi" onClick={onClose}>×</button>
    </div>
  );
}

export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="stepper">
      {steps.map((step, index) => (
        <li key={step} className={index === current ? "current" : index < current ? "complete" : ""} aria-current={index === current ? "step" : undefined}>
          <span>{index < current ? "✓" : index + 1}</span>{step}
        </li>
      ))}
    </ol>
  );
}

export function FileDropzone({ onFile, fileName }: { onFile: (file: File) => void; fileName?: string }) {
  return (
    <label
      className="file-dropzone"
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        const file = event.dataTransfer.files[0];
        if (file) onFile(file);
      }}
    >
      <span>{fileName ?? "Seret file CSV ke sini atau pilih dari perangkat"}</span>
      <span className="secondary-button">Pilih file</span>
      <input type="file" accept=".csv,text/csv" aria-label="Pilih berkas CSV" onChange={(event) => {
        const file = event.target.files?.[0];
        if (file) onFile(file);
      }} />
    </label>
  );
}
