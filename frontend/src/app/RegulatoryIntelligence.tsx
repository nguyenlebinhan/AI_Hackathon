import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  Building2,
  CalendarDays,
  CheckCircle2,
  FileDiff,
  FilePlus2,
  FileText,
  GitBranch,
  Loader2,
  RefreshCw,
  Scale,
  Search,
  Sparkles,
  X,
} from "lucide-react";

import {
  analyzeRegulatoryDocument,
  getRegulatoryIntelligence,
  listRegulatoryDocuments,
  uploadRegulatoryDocument,
  type RegulatoryAnalysis,
  type RegulatoryDocument,
  type RegulatoryIntelligenceData,
  type RegulatoryUploadMetadata,
} from "../api";

type DetailTab = "changes" | "timeline" | "relations";

const STATUS_LABELS: Record<RegulatoryDocument["status"], string> = {
  PARSED: "Chờ phân tích",
  ANALYZED: "Đã phân tích",
  NEEDS_HUMAN_REVIEW: "Cần chuyên viên rà soát",
};

const STATUS_STYLES: Record<RegulatoryDocument["status"], string> = {
  PARSED: "bg-sky-50 text-sky-700",
  ANALYZED: "bg-emerald-50 text-emerald-700",
  NEEDS_HUMAN_REVIEW: "bg-amber-50 text-amber-700",
};

const CHANGE_LABELS: Record<string, string> = {
  ADDED: "Bổ sung",
  REMOVED: "Bãi bỏ",
  MODIFIED: "Điều chỉnh",
  UNCHANGED: "Không đổi",
  MOVED: "Chuyển vị trí",
  RENUMBERED: "Đánh số lại",
  CLARIFIED: "Làm rõ",
  VALUE_CHANGED: "Thay đổi giá trị",
  DEADLINE_CHANGED: "Thay đổi thời hạn",
  RESPONSIBILITY_CHANGED: "Thay đổi trách nhiệm",
  SCOPE_CHANGED: "Thay đổi phạm vi",
  PROCEDURE_CHANGED: "Thay đổi thủ tục",
  LEGAL_BASIS_CHANGED: "Thay đổi căn cứ",
};

function messageOf(reason: unknown): string {
  return reason instanceof Error ? reason.message : "Không thể kết nối tới máy chủ.";
}

function formatDate(value: string): string {
  const date = new Date(value.length === 10 ? `${value}T00:00:00` : value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
}

function factLabel(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/(^|\s)\S/g, letter => letter.toUpperCase());
}

function StatusBadge({ status }: { status: RegulatoryDocument["status"] }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-bold ${STATUS_STYLES[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center px-6 text-center">
      <div className="mb-3 grid h-11 w-11 place-items-center rounded-2xl bg-gray-100 text-gray-400">
        <FileText className="h-5 w-5" />
      </div>
      <p className="text-sm font-bold text-gray-800">{title}</p>
      <p className="mt-1 max-w-md text-xs leading-5 text-gray-500">{description}</p>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-xs font-semibold text-gray-600">
      {label}
      {children}
    </label>
  );
}

function RegulatoryUploadModal({
  onClose,
  onUploaded,
}: {
  onClose: () => void;
  onUploaded: (document: RegulatoryDocument) => void | Promise<void>;
}) {
  const today = new Date().toISOString().slice(0, 10);
  const [file, setFile] = useState<File | null>(null);
  const [form, setForm] = useState({
    familyKey: "",
    title: "",
    documentNumber: "",
    documentType: "",
    issuingAgency: "",
    issuedDate: today,
    effectiveDate: today,
    domain: "",
    applicableSubjects: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function update(key: keyof typeof form, value: string) {
    setForm(current => ({ ...current, [key]: value }));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!file || submitting) return;
    setSubmitting(true);
    setError("");
    const metadata: RegulatoryUploadMetadata = {
      title: form.title.trim(),
      documentNumber: form.documentNumber.trim(),
      documentType: form.documentType.trim(),
      issuingAgency: form.issuingAgency.trim(),
      issuedDate: form.issuedDate,
      effectiveDate: form.effectiveDate,
      domain: form.domain.trim(),
      applicableSubjects: form.applicableSubjects
        .split(",")
        .map(value => value.trim())
        .filter(Boolean),
    };
    if (form.familyKey.trim()) metadata.familyKey = form.familyKey.trim();
    try {
      const document = await uploadRegulatoryDocument(file, metadata);
      await onUploaded(document);
      onClose();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass = "mt-1.5 h-10 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm outline-none focus:border-[#c41e3a]";

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4" onMouseDown={onClose}>
      <form onSubmit={submit} onMouseDown={event => event.stopPropagation()} className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <div>
            <h2 className="font-bold text-gray-900">Thêm văn bản cần theo dõi</h2>
            <p className="mt-1 text-xs text-gray-400">Metadata và nội dung tệp sẽ được gửi trực tiếp tới Regulatory Change API.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-gray-400 hover:bg-gray-100"><X className="h-4 w-4" /></button>
        </div>
        <div className="space-y-5 p-6">
          <label className="flex min-h-28 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-200 bg-gray-50 px-4 text-center hover:border-[#c41e3a]/40">
            <FilePlus2 className="mb-2 h-6 w-6 text-[#c41e3a]" />
            <span className="text-sm font-semibold text-gray-700">{file?.name || "Chọn tệp PDF hoặc DOCX"}</span>
            <span className="mt-1 text-[10px] text-gray-400">Dữ liệu mẫu không được chèn khi API lỗi hoặc trả rỗng.</span>
            <input type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" required className="hidden" onChange={event => setFile(event.target.files?.[0] ?? null)} />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Tên văn bản"><input required value={form.title} onChange={event => update("title", event.target.value)} className={inputClass} /></Field>
            <Field label="Số, ký hiệu"><input required value={form.documentNumber} onChange={event => update("documentNumber", event.target.value)} className={inputClass} /></Field>
            <Field label="Loại văn bản"><input required placeholder="Ví dụ: Nghị định" value={form.documentType} onChange={event => update("documentType", event.target.value)} className={inputClass} /></Field>
            <Field label="Cơ quan ban hành"><input required value={form.issuingAgency} onChange={event => update("issuingAgency", event.target.value)} className={inputClass} /></Field>
            <Field label="Ngày ban hành"><input required type="date" value={form.issuedDate} onChange={event => update("issuedDate", event.target.value)} className={inputClass} /></Field>
            <Field label="Ngày hiệu lực"><input required type="date" value={form.effectiveDate} onChange={event => update("effectiveDate", event.target.value)} className={inputClass} /></Field>
            <Field label="Lĩnh vực"><input required value={form.domain} onChange={event => update("domain", event.target.value)} className={inputClass} /></Field>
            <Field label="Khóa nhóm phiên bản (không bắt buộc)"><input placeholder="Dùng cùng khóa cho các phiên bản" value={form.familyKey} onChange={event => update("familyKey", event.target.value)} className={inputClass} /></Field>
          </div>
          <Field label="Đối tượng áp dụng (phân cách bằng dấu phẩy)"><input value={form.applicableSubjects} onChange={event => update("applicableSubjects", event.target.value)} className={inputClass} /></Field>
          {error && <div role="alert" className="flex gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700"><AlertCircle className="h-4 w-4 flex-shrink-0" />{error}</div>}
        </div>
        <div className="flex justify-end gap-2 border-t border-gray-100 px-6 py-4">
          <button type="button" onClick={onClose} className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-600">Hủy</button>
          <button disabled={!file || submitting} className="flex items-center gap-2 rounded-lg bg-[#c41e3a] px-5 py-2 text-sm font-bold text-white disabled:opacity-50">
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {submitting ? "Đang gửi..." : "Tải lên và nhận diện"}
          </button>
        </div>
      </form>
    </div>
  );
}

function ChangesPanel({ data }: { data: RegulatoryIntelligenceData }) {
  if (data.changes.length === 0) {
    return <EmptyState title="Chưa có thay đổi được ghi nhận" description="Phiên bản đầu tiên hoặc văn bản chưa được phân tích sẽ không có dữ liệu so sánh." />;
  }
  return (
    <div className="space-y-3 p-5">
      {data.changes.map(change => (
        <article key={change.id} className="rounded-xl border border-gray-200 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <span className="rounded-full bg-violet-50 px-2.5 py-1 text-[10px] font-bold text-violet-700">{CHANGE_LABELS[change.changeType] || change.changeType}</span>
              <h4 className="mt-2 text-sm font-bold text-gray-900">{factLabel(change.factKey)}</h4>
            </div>
            <span className="text-[10px] font-semibold text-gray-400">Độ tin cậy {Math.round(change.confidence * 100)}%</span>
          </div>
          <p className="mt-2 text-xs leading-5 text-gray-600">{change.summary}</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg bg-red-50/70 p-3"><p className="text-[10px] font-bold uppercase text-red-500">Giá trị trước</p><p className="mt-1 text-xs text-gray-700">{change.oldValue || "Không có"}</p>{change.oldLocation && <p className="mt-1 text-[10px] text-gray-400">{change.oldLocation}</p>}</div>
            <div className="rounded-lg bg-emerald-50/70 p-3"><p className="text-[10px] font-bold uppercase text-emerald-600">Giá trị mới</p><p className="mt-1 text-xs text-gray-700">{change.newValue || "Không có"}</p>{change.newLocation && <p className="mt-1 text-[10px] text-gray-400">{change.newLocation}</p>}</div>
          </div>
        </article>
      ))}
    </div>
  );
}

function TimelinePanel({ data }: { data: RegulatoryIntelligenceData }) {
  if (data.timeline.length === 0) return <EmptyState title="Chưa có dòng thời gian" description="API chưa trả về phiên bản nào cho nhóm văn bản này." />;
  return (
    <div className="space-y-0 p-5">
      {data.timeline.map((entry, index) => (
        <div key={entry.documentId} className="relative flex gap-4 pb-6 last:pb-0">
          {index < data.timeline.length - 1 && <span className="absolute left-[11px] top-6 h-full w-px bg-gray-200" />}
          <span className="relative mt-1 h-6 w-6 flex-shrink-0 rounded-full border-4 border-white bg-[#c41e3a] shadow" />
          <div className="min-w-0 flex-1 rounded-xl border border-gray-200 p-4">
            <div className="flex flex-wrap justify-between gap-2"><p className="text-sm font-bold text-gray-900">Phiên bản {entry.versionNumber}</p><p className="text-xs text-gray-400">Hiệu lực {formatDate(entry.effectiveDate)}</p></div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {Object.entries(entry.values).map(([key, value]) => <div key={key} className="rounded-lg bg-gray-50 px-3 py-2"><p className="text-[10px] font-semibold text-gray-400">{factLabel(key)}</p><p className="mt-1 text-xs text-gray-700">{value}</p></div>)}
              {Object.keys(entry.values).length === 0 && <p className="text-xs text-gray-400">Không có giá trị định lượng được trích xuất.</p>}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function RelationsPanel({ data }: { data: RegulatoryIntelligenceData }) {
  if (data.legalRelations.length === 0) return <EmptyState title="Chưa tìm thấy quan hệ pháp lý" description="API không trích xuất được văn bản được viện dẫn trong nội dung hiện tại." />;
  return (
    <div className="grid gap-3 p-5 sm:grid-cols-2">
      {data.legalRelations.map((relation, index) => (
        <div key={`${relation.citedReference}-${index}`} className="rounded-xl border border-gray-200 p-4">
          <div className="flex items-start gap-3"><div className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-sky-50 text-sky-700"><GitBranch className="h-4 w-4" /></div><div className="min-w-0"><p className="text-xs font-bold text-gray-900">{relation.citedReference}</p><p className="mt-1 text-[10px] text-gray-400">{relation.relationshipType} · {Math.round(relation.confidence * 100)}%</p></div></div>
          <p className="mt-3 text-[10px] leading-4 text-amber-600">{relation.status.replaceAll("_", " ")}</p>
        </div>
      ))}
    </div>
  );
}

export default function RegulatoryIntelligence({
  onDocumentsChanged,
}: {
  onDocumentsChanged?: () => void | Promise<void>;
}) {
  const [documents, setDocuments] = useState<RegulatoryDocument[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [data, setData] = useState<RegulatoryIntelligenceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<DetailTab>("changes");
  const [showUpload, setShowUpload] = useState(false);
  const [lastAnalysis, setLastAnalysis] = useState<RegulatoryAnalysis | null>(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const values = await listRegulatoryDocuments();
      setDocuments(values);
      setSelectedId(current => values.some(item => item.documentId === current) ? current : values[0]?.documentId ?? null);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (documentId: string) => {
    setDetailLoading(true);
    try {
      setData(await getRegulatoryIntelligence(documentId));
      setError("");
    } catch (reason) {
      setData(null);
      setError(messageOf(reason));
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => { void loadDocuments(); }, [loadDocuments]);
  useEffect(() => {
    if (selectedId) void loadDetail(selectedId);
    else setData(null);
    setLastAnalysis(null);
  }, [loadDetail, selectedId]);

  const selected = documents.find(item => item.documentId === selectedId) ?? null;
  const filtered = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase("vi");
    if (!needle) return documents;
    return documents.filter(document => [document.title, document.documentNumber, document.domain, document.issuingAgency].some(value => value.toLocaleLowerCase("vi").includes(needle)));
  }, [documents, search]);

  async function analyze() {
    if (!selected || analyzing) return;
    setAnalyzing(true);
    setError("");
    setSuccess("");
    try {
      const result = await analyzeRegulatoryDocument(selected.documentId);
      setLastAnalysis(result);
      setSuccess(`Phân tích hoàn tất: ${result.changes.length} thay đổi, ${result.impacts.length} tác động dự án.`);
      await Promise.all([loadDocuments(), loadDetail(selected.documentId)]);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setAnalyzing(false);
    }
  }

  async function uploaded(document: RegulatoryDocument) {
    await loadDocuments();
    setSelectedId(document.documentId);
    setSuccess("Văn bản đã được API tiếp nhận và nhận diện phiên bản thành công.");
    if (onDocumentsChanged) await onDocumentsChanged();
  }

  const analyzedCount = documents.filter(document => document.status === "ANALYZED").length;
  const reviewCount = documents.filter(document => document.status === "NEEDS_HUMAN_REVIEW").length;
  const tabs: Array<{ id: DetailTab; label: string; count: number }> = [
    { id: "changes", label: "Thay đổi", count: data?.changes.length ?? 0 },
    { id: "timeline", label: "Dòng thời gian", count: data?.timeline.length ?? 0 },
    { id: "relations", label: "Quan hệ pháp lý", count: data?.legalRelations.length ?? 0 },
  ];

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-2xl bg-[#0f1623] p-6 text-white">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-white/40">Regulatory Change Intelligence</p><h2 className="mt-2 text-2xl font-bold">Theo dõi thay đổi pháp lý từ dữ liệu thật</h2><p className="mt-2 max-w-2xl text-xs leading-5 text-white/55">Danh sách, tóm tắt, so sánh phiên bản, dòng thời gian và căn cứ viện dẫn đều được tải trực tiếp từ API.</p></div>
          <button type="button" onClick={() => setShowUpload(true)} className="flex items-center justify-center gap-2 rounded-xl bg-[#c41e3a] px-4 py-2.5 text-sm font-bold hover:bg-[#a8172f]"><FilePlus2 className="h-4 w-4" />Thêm văn bản</button>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          {[["Văn bản theo dõi", documents.length, Scale], ["Đã phân tích", analyzedCount, CheckCircle2], ["Cần rà soát", reviewCount, AlertCircle]].map(([label, value, Icon]) => {
            const StatIcon = Icon as React.ElementType;
            return <div key={label as string} className="rounded-xl border border-white/10 bg-white/5 p-4"><div className="flex items-center justify-between"><p className="text-xs text-white/50">{label as string}</p><StatIcon className="h-4 w-4 text-white/35" /></div><p className="mt-2 text-2xl font-bold">{value as number}</p></div>;
          })}
        </div>
      </section>

      {error && <div role="alert" className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"><AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" /><span className="flex-1">{error}</span><button type="button" onClick={() => setError("")}><X className="h-4 w-4" /></button></div>}
      {success && <div className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"><CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0" /><span className="flex-1">{success}</span><button type="button" onClick={() => setSuccess("")}><X className="h-4 w-4" /></button></div>}

      <div className="grid gap-5 xl:grid-cols-[340px_minmax(0,1fr)]">
        <aside className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-100 p-4">
            <div className="flex items-center justify-between"><h3 className="text-sm font-bold text-gray-900">Danh mục văn bản</h3><button type="button" onClick={() => void loadDocuments()} disabled={loading} className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 disabled:opacity-50"><RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /></button></div>
            <div className="relative mt-3"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Tìm số hiệu, lĩnh vực..." className="h-9 w-full rounded-lg border border-gray-200 bg-gray-50 pl-9 pr-3 text-xs outline-none focus:border-[#c41e3a]" /></div>
          </div>
          <div className="max-h-[720px] overflow-y-auto p-2">
            {loading && documents.length === 0 ? <div className="flex min-h-48 items-center justify-center gap-2 text-xs text-gray-400"><Loader2 className="h-4 w-4 animate-spin" />Đang tải từ API...</div> : filtered.length === 0 ? <EmptyState title="Chưa có văn bản" description="Tải văn bản pháp lý đầu tiên để bắt đầu theo dõi phiên bản." /> : filtered.map(document => (
              <button type="button" key={document.id} onClick={() => setSelectedId(document.documentId)} className={`mb-2 w-full rounded-xl border p-3 text-left transition ${selectedId === document.documentId ? "border-[#c41e3a]/30 bg-red-50/50" : "border-transparent hover:bg-gray-50"}`}>
                <div className="flex items-start gap-3"><div className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-gray-100 text-gray-500"><FileText className="h-4 w-4" /></div><div className="min-w-0 flex-1"><p className="truncate text-xs font-bold text-gray-900">{document.title}</p><p className="mt-1 truncate text-[10px] text-gray-400">{document.documentNumber} · Phiên bản {document.versionNumber}</p><div className="mt-2"><StatusBadge status={document.status} /></div></div><ArrowRight className="mt-2 h-3.5 w-3.5 text-gray-300" /></div>
              </button>
            ))}
          </div>
        </aside>

        <section className="min-w-0 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          {!selected ? <EmptyState title="Chọn một văn bản" description="Thông tin phân tích do API trả về sẽ xuất hiện tại đây." /> : detailLoading ? <div className="flex min-h-[560px] items-center justify-center gap-2 text-sm text-gray-400"><Loader2 className="h-5 w-5 animate-spin" />Đang tải dữ liệu intelligence...</div> : !data ? <EmptyState title="Không tải được chi tiết" description="Hãy thử làm mới hoặc chọn lại văn bản." /> : (
            <>
              <div className="border-b border-gray-100 p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><StatusBadge status={selected.status} /><span className="text-[10px] font-semibold uppercase text-gray-400">{selected.documentType}</span></div><h3 className="mt-3 text-xl font-bold text-gray-900">{selected.title}</h3><p className="mt-1 text-xs text-gray-500">{selected.documentNumber} · {selected.issuingAgency}</p></div>
                  <button type="button" onClick={() => void analyze()} disabled={analyzing} className="flex flex-shrink-0 items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-xs font-bold text-white hover:bg-violet-700 disabled:opacity-50">{analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}{analyzing ? "Đang phân tích..." : "Phân tích thay đổi"}</button>
                </div>
                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  <div className="flex gap-2 rounded-xl bg-gray-50 p-3"><CalendarDays className="mt-0.5 h-4 w-4 text-gray-400" /><div><p className="text-[10px] text-gray-400">Ngày hiệu lực</p><p className="mt-1 text-xs font-semibold text-gray-700">{formatDate(selected.effectiveDate)}</p></div></div>
                  <div className="flex gap-2 rounded-xl bg-gray-50 p-3"><Building2 className="mt-0.5 h-4 w-4 text-gray-400" /><div><p className="text-[10px] text-gray-400">Lĩnh vực</p><p className="mt-1 text-xs font-semibold text-gray-700">{selected.domain}</p></div></div>
                  <div className="flex gap-2 rounded-xl bg-gray-50 p-3"><GitBranch className="mt-0.5 h-4 w-4 text-gray-400" /><div><p className="text-[10px] text-gray-400">Lịch sử phiên bản</p><p className="mt-1 text-xs font-semibold text-gray-700">{data.versions.length} phiên bản</p></div></div>
                </div>
                <div className="mt-5 rounded-xl border border-sky-100 bg-sky-50/60 p-4"><p className="text-[10px] font-bold uppercase tracking-wide text-sky-700">Tóm tắt điều hành từ API</p><p className="mt-2 whitespace-pre-wrap text-xs leading-5 text-gray-700">{data.summary.executiveSummary || "API chưa tạo tóm tắt cho văn bản này."}</p></div>
                {Object.keys(data.summary.importantValues).length > 0 && <div className="mt-4 grid gap-2 sm:grid-cols-2">{Object.entries(data.summary.importantValues).map(([key, value]) => <div key={key} className="rounded-lg border border-gray-100 px-3 py-2"><p className="text-[10px] font-semibold text-gray-400">{factLabel(key)}</p><p className="mt-1 text-xs font-bold text-gray-700">{value}</p></div>)}</div>}
                {lastAnalysis && <div className="mt-4 flex items-center gap-2 rounded-xl bg-violet-50 px-4 py-3 text-xs text-violet-700"><FileDiff className="h-4 w-4" />Lần chạy {lastAnalysis.run.id}: {lastAnalysis.run.status}, {lastAnalysis.impacts.length} tác động dự án.</div>}
              </div>
              <div className="flex gap-1 overflow-x-auto border-b border-gray-100 px-4 pt-3">
                {tabs.map(item => <button type="button" key={item.id} onClick={() => setTab(item.id)} className={`whitespace-nowrap border-b-2 px-3 py-2 text-xs font-bold ${tab === item.id ? "border-[#c41e3a] text-[#c41e3a]" : "border-transparent text-gray-400 hover:text-gray-700"}`}>{item.label} <span className="ml-1 rounded-full bg-gray-100 px-1.5 py-0.5 text-[9px] text-gray-500">{item.count}</span></button>)}
              </div>
              {tab === "changes" && <ChangesPanel data={data} />}
              {tab === "timeline" && <TimelinePanel data={data} />}
              {tab === "relations" && <RelationsPanel data={data} />}
            </>
          )}
        </section>
      </div>
      {showUpload && <RegulatoryUploadModal onClose={() => setShowUpload(false)} onUploaded={uploaded} />}
    </div>
  );
}
