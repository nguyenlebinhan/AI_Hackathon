import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Database,
  FileText,
  Filter,
  GitBranch,
  Loader2,
  Network,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

import {
  ApiError,
  generateKnowledgeGraph,
  getKnowledgeGraph,
  type DocumentPublic,
  type KnowledgeGraph,
  type KnowledgeGraphCitation,
  type KnowledgeGraphEdge,
  type KnowledgeGraphNode,
} from "../api";

type SelectedElement =
  | { kind: "node"; id: string }
  | { kind: "edge"; id: string }
  | null;

const READY_STATUSES = new Set<DocumentPublic["status"]>(["COMPLETED", "NEEDS_REVIEW"]);

const IMPORTANCE_STYLES: Record<KnowledgeGraphNode["importance"], string> = {
  LOW: "bg-gray-100 text-gray-600",
  MEDIUM: "bg-sky-50 text-sky-700",
  HIGH: "bg-amber-50 text-amber-700",
  CRITICAL: "bg-red-50 text-red-700",
};

function messageOf(reason: unknown): string {
  return reason instanceof Error ? reason.message : "Không thể kết nối tới máy chủ.";
}

function humanize(value: string): string {
  return value
    .replaceAll("_", " ")
    .toLocaleLowerCase("vi")
    .replace(/(^|\s)\S/g, letter => letter.toLocaleUpperCase("vi"));
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Không có dữ liệu";
  if (Array.isArray(value)) return value.map(displayValue).join(", ");
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

function nodeColors(type: string): { fill: string; stroke: string; text: string } {
  if (["LEGAL_DOCUMENT", "LEGAL_PROVISION", "LEGAL_REFERENCE"].includes(type)) {
    return { fill: "#fff1f2", stroke: "#e11d48", text: "#9f1239" };
  }
  if (["AGENCY", "PERSON", "ROLE"].includes(type)) {
    return { fill: "#eff6ff", stroke: "#2563eb", text: "#1e40af" };
  }
  if (["TASK", "RESPONSIBILITY", "AUTHORITY", "PROCEDURE"].includes(type)) {
    return { fill: "#f5f3ff", stroke: "#7c3aed", text: "#5b21b6" };
  }
  if (["DEADLINE", "EFFECTIVE_DATE"].includes(type)) {
    return { fill: "#fffbeb", stroke: "#d97706", text: "#92400e" };
  }
  if (["FUNDING_SOURCE", "BUDGET"].includes(type)) {
    return { fill: "#ecfdf5", stroke: "#059669", text: "#065f46" };
  }
  return { fill: "#f8fafc", stroke: "#64748b", text: "#334155" };
}

function nodePositions(nodes: KnowledgeGraphNode[]) {
  const centerX = 500;
  const centerY = 310;
  const byId = new Map<string, { x: number; y: number }>();
  if (nodes.length === 1) {
    byId.set(nodes[0].id, { x: centerX, y: centerY });
    return byId;
  }
  nodes.forEach((node, index) => {
    const angle = index * Math.PI * (3 - Math.sqrt(5)) - Math.PI / 2;
    const radius = Math.min(48 * Math.sqrt(index + 1), 270);
    byId.set(node.id, {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
    });
  });
  return byId;
}

function GraphCanvas({
  nodes,
  edges,
  selected,
  onSelect,
  zoom,
}: {
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  selected: SelectedElement;
  onSelect: (value: SelectedElement) => void;
  zoom: number;
}) {
  const positions = useMemo(() => nodePositions(nodes), [nodes]);
  const selectedNodeId = selected?.kind === "node" ? selected.id : null;
  const connectedIds = useMemo(() => {
    if (!selectedNodeId) return new Set<string>();
    const values = new Set<string>([selectedNodeId]);
    edges.forEach(edge => {
      if (edge.sourceNodeId === selectedNodeId) values.add(edge.targetNodeId);
      if (edge.targetNodeId === selectedNodeId) values.add(edge.sourceNodeId);
    });
    return values;
  }, [edges, selectedNodeId]);

  return (
    <div className="overflow-auto rounded-xl border border-gray-100 bg-[radial-gradient(circle_at_center,_#ffffff,_#f8fafc)]">
      <svg viewBox="0 0 1000 620" className="min-h-[560px] min-w-[800px]" role="img" aria-label="Đồ thị tri thức của tài liệu">
        <defs>
          <marker id="graph-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L8,4 L0,8 z" fill="#94a3b8" />
          </marker>
          <filter id="node-shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.12" />
          </filter>
        </defs>
        <g transform={`translate(500 310) scale(${zoom}) translate(-500 -310)`}>
          {edges.map(edge => {
            const source = positions.get(edge.sourceNodeId);
            const target = positions.get(edge.targetNodeId);
            if (!source || !target) return null;
            const isSelected = selected?.kind === "edge" && selected.id === edge.id;
            const isConnected = selectedNodeId === edge.sourceNodeId || selectedNodeId === edge.targetNodeId;
            const faded = selectedNodeId !== null && !isConnected;
            return (
              <g key={edge.id} className="cursor-pointer" onClick={() => onSelect({ kind: "edge", id: edge.id })}>
                <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke="transparent" strokeWidth="14" />
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={isSelected ? "#c41e3a" : isConnected ? "#7c3aed" : "#94a3b8"}
                  strokeWidth={isSelected || isConnected ? 2.5 : 1.4}
                  strokeDasharray={edge.verificationStatus === "NEEDS_REVIEW" ? "6 4" : undefined}
                  markerEnd="url(#graph-arrow)"
                  opacity={faded ? 0.16 : 0.8}
                />
              </g>
            );
          })}
          {nodes.map(node => {
            const point = positions.get(node.id);
            if (!point) return null;
            const colors = nodeColors(node.type);
            const isSelected = selectedNodeId === node.id;
            const faded = selectedNodeId !== null && !connectedIds.has(node.id);
            const label = node.name.length > 22 ? `${node.name.slice(0, 21)}…` : node.name;
            return (
              <g
                key={node.id}
                role="button"
                tabIndex={0}
                className="cursor-pointer outline-none"
                opacity={faded ? 0.24 : 1}
                onClick={() => onSelect({ kind: "node", id: node.id })}
                onKeyDown={event => {
                  if (event.key === "Enter" || event.key === " ") onSelect({ kind: "node", id: node.id });
                }}
              >
                <rect
                  x={point.x - 72}
                  y={point.y - 27}
                  width="144"
                  height="54"
                  rx="13"
                  fill={colors.fill}
                  stroke={isSelected ? "#c41e3a" : colors.stroke}
                  strokeWidth={isSelected ? 3 : node.importance === "CRITICAL" ? 2.5 : 1.5}
                  filter="url(#node-shadow)"
                />
                <text x={point.x} y={point.y - 3} textAnchor="middle" fontSize="11" fontWeight="700" fill={colors.text}>{label}</text>
                <text x={point.x} y={point.y + 13} textAnchor="middle" fontSize="8" fontWeight="600" fill="#94a3b8">{humanize(node.type)}</text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}

function CitationList({ citations }: { citations: KnowledgeGraphCitation[] }) {
  if (citations.length === 0) {
    return <p className="rounded-lg bg-gray-50 px-3 py-4 text-center text-xs text-gray-400">Không có trích dẫn được API trả về.</p>;
  }
  return (
    <div className="space-y-2">
      {citations.map(citation => (
        <div key={citation.id} className="rounded-xl border border-gray-100 bg-gray-50/60 p-3">
          <div className="flex items-center justify-between gap-2 text-[10px] font-semibold text-gray-400">
            <span>{[citation.article, citation.clause, citation.point].filter(Boolean).join(" · ") || "Trích dẫn"}</span>
            <span>Trang {citation.page}</span>
          </div>
          <p className="mt-2 text-xs leading-5 text-gray-600">{citation.quote}</p>
          <p className="mt-2 text-[10px] text-emerald-600">Độ tin cậy nguồn {Math.round(citation.sourceConfidence * 100)}%</p>
        </div>
      ))}
    </div>
  );
}

function Inspector({ graph, selected, onSelect }: {
  graph: KnowledgeGraph;
  selected: SelectedElement;
  onSelect: (value: SelectedElement) => void;
}) {
  const node = selected?.kind === "node" ? graph.nodes.find(item => item.id === selected.id) ?? null : null;
  const edge = selected?.kind === "edge" ? graph.edges.find(item => item.id === selected.id) ?? null : null;

  if (!node && !edge) {
    return (
      <div className="flex min-h-72 flex-col items-center justify-center p-6 text-center">
        <Network className="mb-3 h-7 w-7 text-gray-300" />
        <p className="text-sm font-bold text-gray-700">Chọn một phần tử</p>
        <p className="mt-1 text-xs leading-5 text-gray-400">Nhấn vào node hoặc đường liên kết để xem thuộc tính và bằng chứng.</p>
      </div>
    );
  }

  const source = edge ? graph.nodes.find(item => item.id === edge.sourceNodeId) : null;
  const target = edge ? graph.nodes.find(item => item.id === edge.targetNodeId) : null;
  const properties = node?.properties ?? edge?.properties ?? {};
  const citations = node?.citations ?? edge?.citations ?? [];
  const relationships = node
    ? graph.edges.filter(item => item.sourceNodeId === node.id || item.targetNodeId === node.id)
    : [];

  return (
    <div>
      <div className="border-b border-gray-100 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-wide text-gray-400">{node ? "Thực thể" : "Quan hệ"}</p>
            <h3 className="mt-1 break-words text-sm font-bold text-gray-900">{node?.name ?? humanize(edge?.type ?? "")}</h3>
          </div>
          <button type="button" onClick={() => onSelect(null)} className="rounded p-1 text-gray-400 hover:bg-gray-100"><X className="h-4 w-4" /></button>
        </div>
        {node && <div className="mt-3 flex flex-wrap gap-2"><span className="rounded-full bg-violet-50 px-2.5 py-1 text-[10px] font-bold text-violet-700">{humanize(node.type)}</span><span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${IMPORTANCE_STYLES[node.importance]}`}>{humanize(node.importance)}</span></div>}
        {edge && <div className="mt-3 rounded-lg bg-gray-50 p-3 text-xs text-gray-600"><button type="button" onClick={() => source && onSelect({ kind: "node", id: source.id })} className="font-bold text-violet-700">{source?.name || edge.sourceNodeId}</button><span className="mx-2 text-gray-300">→</span><button type="button" onClick={() => target && onSelect({ kind: "node", id: target.id })} className="font-bold text-violet-700">{target?.name || edge.targetNodeId}</button></div>}
        <div className="mt-3 flex items-center gap-2 text-[10px] text-gray-400"><ShieldCheck className="h-3.5 w-3.5" />Độ tin cậy {Math.round((node?.confidence ?? edge?.confidence ?? 0) * 100)}%{edge && ` · ${humanize(edge.verificationStatus)}`}</div>
      </div>
      <div className="max-h-[610px] space-y-5 overflow-y-auto p-4">
        <section><h4 className="mb-2 text-[10px] font-bold uppercase tracking-wide text-gray-500">Thuộc tính</h4>{Object.keys(properties).length === 0 ? <p className="text-xs text-gray-400">Không có thuộc tính bổ sung.</p> : <div className="space-y-2">{Object.entries(properties).map(([key, value]) => <div key={key} className="rounded-lg bg-gray-50 px-3 py-2"><p className="text-[10px] font-semibold text-gray-400">{humanize(key)}</p><p className="mt-1 whitespace-pre-wrap break-words text-xs text-gray-700">{displayValue(value)}</p></div>)}</div>}</section>
        {node && <section><h4 className="mb-2 text-[10px] font-bold uppercase tracking-wide text-gray-500">Quan hệ ({relationships.length})</h4><div className="space-y-1.5">{relationships.map(item => { const otherId = item.sourceNodeId === node.id ? item.targetNodeId : item.sourceNodeId; const other = graph.nodes.find(value => value.id === otherId); return <button type="button" key={item.id} onClick={() => onSelect({ kind: "edge", id: item.id })} className="flex w-full items-center gap-2 rounded-lg border border-gray-100 px-3 py-2 text-left hover:bg-gray-50"><GitBranch className="h-3.5 w-3.5 flex-shrink-0 text-violet-500" /><span className="min-w-0 flex-1"><span className="block text-[10px] font-bold text-gray-500">{humanize(item.type)}</span><span className="block truncate text-xs text-gray-700">{other?.name || otherId}</span></span></button>; })}{relationships.length === 0 && <p className="text-xs text-gray-400">Node chưa có quan hệ.</p>}</div></section>}
        <section><h4 className="mb-2 text-[10px] font-bold uppercase tracking-wide text-gray-500">Bằng chứng ({citations.length})</h4><CitationList citations={citations} /></section>
      </div>
    </div>
  );
}

export default function KnowledgeGraphScreen({ documents }: { documents: DocumentPublic[] }) {
  const readyDocuments = useMemo(() => documents.filter(document => READY_STATUSES.has(document.status)), [documents]);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [selected, setSelected] = useState<SelectedElement>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [privateProcessing, setPrivateProcessing] = useState(false);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    setDocumentId(current => readyDocuments.some(document => document.id === current) ? current : readyDocuments[0]?.id ?? null);
  }, [readyDocuments]);

  const loadGraph = useCallback(async (selectedDocumentId: string) => {
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const value = await getKnowledgeGraph(selectedDocumentId);
      setGraph(value);
      setSelected(value.nodes[0] ? { kind: "node", id: value.nodes[0].id } : null);
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 404) {
        setGraph(null);
        setSelected(null);
      } else {
        setGraph(null);
        setError(messageOf(reason));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setSearch("");
    setTypeFilter("ALL");
    setZoom(1);
    if (documentId) void loadGraph(documentId);
    else {
      setGraph(null);
      setSelected(null);
    }
  }, [documentId, loadGraph]);

  async function generate() {
    if (!documentId || generating) return;
    setGenerating(true);
    setError("");
    setSuccess("");
    try {
      const result = await generateKnowledgeGraph(documentId, privateProcessing);
      if (!result.graph) {
        setGraph(null);
        setError(`Workflow ${result.workflowId} kết thúc nhưng chưa tạo được đồ thị. Hãy kiểm tra cấu hình model hoặc dữ liệu chunk.`);
        return;
      }
      setGraph(result.graph);
      setSelected(result.graph.nodes[0] ? { kind: "node", id: result.graph.nodes[0].id } : null);
      setSuccess(`Đã tạo Knowledge Graph phiên bản ${result.graph.version} với ${result.graph.nodes.length} node và ${result.graph.edges.length} quan hệ.`);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setGenerating(false);
    }
  }

  const nodeTypes = useMemo(() => graph ? [...new Set(graph.nodes.map(node => node.type))].sort() : [], [graph]);
  const visibleNodes = useMemo(() => {
    if (!graph) return [];
    const needle = search.trim().toLocaleLowerCase("vi");
    return graph.nodes.filter(node => {
      const matchesType = typeFilter === "ALL" || node.type === typeFilter;
      const matchesSearch = !needle || [node.name, node.canonicalName, node.type].some(value => value.toLocaleLowerCase("vi").includes(needle));
      return matchesType && matchesSearch;
    });
  }, [graph, search, typeFilter]);
  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map(node => node.id)), [visibleNodes]);
  const visibleEdges = useMemo(() => graph?.edges.filter(edge => visibleNodeIds.has(edge.sourceNodeId) && visibleNodeIds.has(edge.targetNodeId)) ?? [], [graph, visibleNodeIds]);
  const selectedDocument = readyDocuments.find(document => document.id === documentId) ?? null;

  return (
    <div className="space-y-5">
      <section className="rounded-2xl bg-[#0f1623] p-6 text-white shadow-sm">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-white/40">Knowledge Graph API</p><h2 className="mt-2 text-2xl font-bold">Đồ thị tri thức tài liệu</h2><p className="mt-2 max-w-2xl text-xs leading-5 text-white/55">Thực thể, quan hệ, mức độ quan trọng và trích dẫn dưới đây được tải trực tiếp từ API, không có graph mẫu.</p></div>
          <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-center"><label className="flex items-center gap-2 text-xs text-white/55"><input type="checkbox" checked={privateProcessing} onChange={event => setPrivateProcessing(event.target.checked)} className="accent-[#c41e3a]" />Xử lý riêng tư</label><button type="button" disabled={!documentId || generating} onClick={() => void generate()} className="flex items-center justify-center gap-2 rounded-xl bg-[#c41e3a] px-4 py-2.5 text-sm font-bold hover:bg-[#a8172f] disabled:opacity-50">{generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}{generating ? "Đang sinh graph..." : graph ? "Tạo phiên bản mới" : "Sinh Knowledge Graph"}</button></div>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-4">
          {[["Phiên bản", graph?.version ?? 0, Database], ["Thực thể", graph?.nodes.length ?? 0, Network], ["Quan hệ", graph?.edges.length ?? 0, GitBranch], ["Cần rà soát", graph?.edges.filter(edge => edge.verificationStatus === "NEEDS_REVIEW").length ?? 0, AlertCircle]].map(([label, value, Icon]) => { const StatIcon = Icon as React.ElementType; return <div key={label as string} className="rounded-xl border border-white/10 bg-white/5 p-4"><div className="flex items-center justify-between"><p className="text-xs text-white/50">{label as string}</p><StatIcon className="h-4 w-4 text-white/35" /></div><p className="mt-2 text-2xl font-bold">{value as number}</p></div>; })}
        </div>
      </section>

      {error && <div role="alert" className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"><AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" /><span className="flex-1">{error}</span><button type="button" onClick={() => setError("")}><X className="h-4 w-4" /></button></div>}
      {success && <div className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"><CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0" /><span className="flex-1">{success}</span><button type="button" onClick={() => setSuccess("")}><X className="h-4 w-4" /></button></div>}

      <div className="grid gap-5 xl:grid-cols-[260px_minmax(0,1fr)_300px]">
        <aside className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-100 p-4"><h3 className="text-sm font-bold text-gray-900">Tài liệu đã xử lý</h3><p className="mt-1 text-[10px] text-gray-400">{readyDocuments.length} nguồn có thể tạo graph</p></div>
          <div className="max-h-[720px] overflow-y-auto p-2">
            {readyDocuments.length === 0 ? <div className="p-6 text-center"><FileText className="mx-auto h-6 w-6 text-gray-300" /><p className="mt-3 text-xs font-bold text-gray-600">Chưa có tài liệu sẵn sàng</p><p className="mt-1 text-[10px] leading-4 text-gray-400">Graph chỉ được tạo từ tài liệu đã xử lý xong.</p></div> : readyDocuments.map(document => <button type="button" key={document.id} onClick={() => setDocumentId(document.id)} className={`mb-2 w-full rounded-xl border p-3 text-left ${documentId === document.id ? "border-[#c41e3a]/30 bg-red-50/50" : "border-transparent hover:bg-gray-50"}`}><div className="flex items-start gap-2.5"><div className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-lg bg-gray-100 text-gray-500"><FileText className="h-3.5 w-3.5" /></div><div className="min-w-0"><p className="truncate text-xs font-bold text-gray-800">{document.title}</p><p className="mt-1 text-[10px] text-gray-400">{document.status === "NEEDS_REVIEW" ? "Cần rà soát" : "Đã xử lý"}</p></div></div></button>)}
          </div>
        </aside>

        <section className="min-w-0 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          <div className="flex flex-col gap-3 border-b border-gray-100 p-4 lg:flex-row lg:items-center">
            <div className="min-w-0 flex-1"><h3 className="truncate text-sm font-bold text-gray-900">{selectedDocument?.title || "Chưa chọn tài liệu"}</h3>{graph && <p className="mt-1 text-[10px] text-gray-400">Graph v{graph.version} · {humanize(graph.status)} · {formatDate(graph.createdAt)}</p>}</div>
            {graph && <div className="flex flex-wrap items-center gap-2"><div className="relative"><Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Tìm node" className="h-9 w-40 rounded-lg border border-gray-200 pl-8 pr-2 text-xs outline-none focus:border-[#c41e3a]" /></div><div className="relative"><Filter className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" /><select value={typeFilter} onChange={event => setTypeFilter(event.target.value)} className="h-9 max-w-44 rounded-lg border border-gray-200 bg-white pl-8 pr-2 text-xs outline-none"><option value="ALL">Tất cả loại</option>{nodeTypes.map(type => <option key={type} value={type}>{humanize(type)}</option>)}</select></div><button type="button" title="Thu nhỏ" onClick={() => setZoom(value => Math.max(0.65, value - 0.1))} className="rounded-lg border border-gray-200 p-2 text-gray-500"><ZoomOut className="h-4 w-4" /></button><button type="button" title="Phóng to" onClick={() => setZoom(value => Math.min(1.5, value + 0.1))} className="rounded-lg border border-gray-200 p-2 text-gray-500"><ZoomIn className="h-4 w-4" /></button><button type="button" title="Làm mới" onClick={() => documentId && void loadGraph(documentId)} className="rounded-lg border border-gray-200 p-2 text-gray-500"><RefreshCw className="h-4 w-4" /></button></div>}
          </div>
          {loading ? <div className="flex min-h-[560px] items-center justify-center gap-2 text-sm text-gray-400"><Loader2 className="h-5 w-5 animate-spin" />Đang tải Knowledge Graph...</div> : !documentId ? <div className="flex min-h-[560px] flex-col items-center justify-center p-8 text-center"><Network className="h-10 w-10 text-gray-200" /><p className="mt-4 text-sm font-bold text-gray-700">Chưa có nguồn dữ liệu</p></div> : !graph ? <div className="flex min-h-[560px] flex-col items-center justify-center p-8 text-center"><Network className="h-10 w-10 text-gray-200" /><p className="mt-4 text-sm font-bold text-gray-700">Tài liệu chưa có Knowledge Graph</p><p className="mt-1 max-w-sm text-xs leading-5 text-gray-400">API trả về trạng thái chưa có dữ liệu. Nhấn “Sinh Knowledge Graph” để chạy workflow.</p><button type="button" disabled={generating} onClick={() => void generate()} className="mt-5 flex items-center gap-2 rounded-lg bg-[#c41e3a] px-4 py-2 text-xs font-bold text-white"><Sparkles className="h-3.5 w-3.5" />Sinh graph</button></div> : visibleNodes.length === 0 ? <div className="flex min-h-[560px] items-center justify-center text-sm text-gray-400">Không có node phù hợp bộ lọc.</div> : <GraphCanvas nodes={visibleNodes} edges={visibleEdges} selected={selected} onSelect={setSelected} zoom={zoom} />}
          {graph && <div className="flex flex-wrap items-center gap-4 border-t border-gray-100 px-4 py-3 text-[10px] text-gray-400"><span>Hiển thị {visibleNodes.length}/{graph.nodes.length} node</span><span>{visibleEdges.length}/{graph.edges.length} quan hệ</span><span>Zoom {Math.round(zoom * 100)}%</span><span className="ml-auto">Đường nét đứt: quan hệ cần rà soát</span></div>}
        </section>

        <aside className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">{graph ? <Inspector graph={graph} selected={selected} onSelect={setSelected} /> : <div className="flex min-h-72 items-center justify-center p-6 text-center text-xs text-gray-400">Chi tiết phần tử sẽ xuất hiện sau khi API trả về graph.</div>}</aside>
      </div>
    </div>
  );
}
