// SVG schematic city map — works fully offline (no external tile provider).
// Bins are plotted by real lat/lng; the latest route is drawn as a polyline.
// Swap-in for Leaflet + OSM tiles is documented in the project README.

import { useMemo, useState } from "react";
import type { Bin, Depot, RouteStop } from "../types";

interface Props {
  bins: Bin[];
  depot: Depot | null;
  stops?: RouteStop[];
  selectedBinId?: string | null;
  onSelectBin?: (binId: string) => void;
  height?: number;
}

const W = 900;
const H = 560;
const PAD = 60;

const STATUS_FILL: Record<string, string> = {
  CRITICAL: "#dc2626",
  WARNING: "#d97706",
  NORMAL: "#059669",
};

export default function CityMap({
  bins,
  depot,
  stops = [],
  selectedBinId,
  onSelectBin,
  height,
}: Props) {
  const [hover, setHover] = useState<string | null>(null);

  const { project, zones } = useMemo(() => {
    const pts = [
      ...bins.map((b) => ({ lat: b.latitude, lng: b.longitude })),
      ...(depot ? [{ lat: depot.latitude, lng: depot.longitude }] : []),
    ];
    const lats = pts.map((p) => p.lat);
    const lngs = pts.map((p) => p.lng);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);
    const spanLat = maxLat - minLat || 0.01;
    const spanLng = maxLng - minLng || 0.01;

    const project = (lat: number, lng: number): [number, number] => [
      PAD + ((lng - minLng) / spanLng) * (W - 2 * PAD),
      H - PAD - ((lat - minLat) / spanLat) * (H - 2 * PAD),
    ];

    const zoneSet = new Map<string, { x: number; y: number; n: number }>();
    for (const b of bins) {
      const [x, y] = project(b.latitude, b.longitude);
      const z = zoneSet.get(b.zone) ?? { x: 0, y: 0, n: 0 };
      zoneSet.set(b.zone, { x: z.x + x, y: z.y + y, n: z.n + 1 });
    }
    const zones = [...zoneSet.entries()].map(([name, { x, y, n }]) => ({
      name,
      x: x / n,
      y: y / n,
    }));
    return { project, zones };
  }, [bins, depot]);

  const binById = useMemo(() => new Map(bins.map((b) => [b.id, b])), [bins]);

  // Route polyline: depot → stops in order → depot
  const routePath = useMemo(() => {
    if (!depot || stops.length === 0) return "";
    const pts: [number, number][] = [project(depot.latitude, depot.longitude)];
    for (const s of stops) {
      const b = binById.get(s.bin_id);
      if (b) pts.push(project(b.latitude, b.longitude));
    }
    pts.push(project(depot.latitude, depot.longitude));
    return pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  }, [depot, stops, binById, project]);

  const stopSeq = useMemo(() => {
    const m = new Map<string, number>();
    stops.forEach((s) => m.set(s.bin_id, s.sequence));
    return m;
  }, [stops]);

  return (
    <div className="relative overflow-hidden rounded-2xl border border-edge bg-[#edf2f9]">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={height ? { height } : undefined}
        className="w-full"
        role="img"
        aria-label="City map with bin locations"
      >
        <defs>
          <pattern id="grid" width="45" height="45" patternUnits="userSpaceOnUse">
            <path d="M45 0H0V45" fill="none" stroke="#e3eaf3" strokeWidth="1" />
          </pattern>
          <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0 0L10 5L0 10z" fill="#65a30d" />
          </marker>
        </defs>
        <rect width={W} height={H} fill="url(#grid)" />

        {/* zone labels */}
        {zones.map((z) => (
          <text
            key={z.name}
            x={z.x}
            y={z.y - 46}
            textAnchor="middle"
            style={{ fontSize: 11, letterSpacing: 3, fill: "#93a3ba", textTransform: "uppercase" }}
          >
            {z.name}
          </text>
        ))}

        {/* route */}
        {routePath && (
          <>
            <path d={routePath} fill="none" stroke="#65a30d" strokeWidth={2.5} strokeOpacity={0.25} />
            <path
              d={routePath}
              fill="none"
              stroke="#65a30d"
              strokeWidth={2}
              strokeDasharray="7 6"
              marker-mid="url(#arrow)"
            />
          </>
        )}

        {/* depot */}
        {depot &&
          (() => {
            const [x, y] = project(depot.latitude, depot.longitude);
            return (
              <g>
                <rect
                  x={x - 11}
                  y={y - 11}
                  width={22}
                  height={22}
                  rx={5}
                  fill="#ffffff"
                  stroke="#0284c7"
                  strokeWidth={2}
                />
                <text x={x} y={y + 4} textAnchor="middle" style={{ fontSize: 11, fill: "#0284c7" }}>
                  ▣
                </text>
                <text x={x} y={y - 18} textAnchor="middle" style={{ fontSize: 10, fill: "#0284c7" }}>
                  {depot.name.replace(" (Demo)", "")}
                </text>
              </g>
            );
          })()}

        {/* bins */}
        {bins.map((b) => {
          const [x, y] = project(b.latitude, b.longitude);
          const fill = b.is_stale ? "#7c3aed" : STATUS_FILL[b.status ?? "NORMAL"] ?? "#059669";
          const r = 13;
          const circ = 2 * Math.PI * 10;
          const isSel = selectedBinId === b.id;
          const isHover = hover === b.id;
          const seq = stopSeq.get(b.id);
          return (
            <g
              key={b.id}
              onClick={() => onSelectBin?.(b.id)}
              onMouseEnter={() => setHover(b.id)}
              onMouseLeave={() => setHover(null)}
              style={{ cursor: onSelectBin ? "pointer" : "default" }}
            >
              {(isSel || isHover) && <circle cx={x} cy={y} r={r + 6} fill={fill} fillOpacity={0.15} />}
              <circle cx={x} cy={y} r={r} fill="#ffffff" stroke={fill} strokeWidth={2} />
              {/* fill level arc */}
              <circle
                cx={x}
                cy={y}
                r={10}
                fill="none"
                stroke={fill}
                strokeWidth={3}
                strokeDasharray={`${(circ * (b.fill_percent ?? 0)) / 100} ${circ}`}
                strokeLinecap="round"
                transform={`rotate(-90 ${x} ${y})`}
                opacity={0.9}
              />
              <text
                x={x}
                y={y + 3.5}
                textAnchor="middle"
                style={{ fontSize: 9, fontWeight: 700, fill: "#17233c" }}
              >
                {Math.round(b.fill_percent ?? 0)}
              </text>
              {seq !== undefined && (
                <g>
                  <circle cx={x + r + 2} cy={y - r - 2} r={8} fill="#65a30d" />
                  <text
                    x={x + r + 2}
                    y={y - r + 1}
                    textAnchor="middle"
                    style={{ fontSize: 9, fontWeight: 800, fill: "#ffffff" }}
                  >
                    {seq}
                  </text>
                </g>
              )}
              {(isHover || isSel) && (
                <text x={x} y={y + r + 14} textAnchor="middle" style={{ fontSize: 10, fill: "#17233c" }}>
                  {b.name.replace(" (Demo)", "")}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* legend */}
      <div className="absolute bottom-3 left-3 flex flex-wrap gap-x-4 gap-y-1 rounded-xl border border-edge bg-abyss/80 px-3 py-2 text-[10px] text-dim backdrop-blur">
        <span className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-critical" /> Critical ≥90%</span>
        <span className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-warning" /> Warning ≥70%</span>
        <span className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-normal" /> Normal</span>
        <span className="flex items-center gap-1.5"><i className="size-2 rounded-full bg-stale" /> Stale sensor</span>
        <span className="flex items-center gap-1.5"><i className="size-2 rounded-sm border border-peri bg-panel" /> Depot</span>
        <span className="text-dim/60">Schematic map (offline) · distances: haversine × road factor</span>
      </div>
    </div>
  );
}
