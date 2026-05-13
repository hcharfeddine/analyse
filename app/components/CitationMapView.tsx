'use client';

import React, { useEffect, useRef, useState } from 'react';
import { GraphSkeleton, ErrorState } from './LoadingStates';

interface Manifest {
  available: boolean;
  min_x?: number;
  max_x?: number;
  min_y?: number;
  max_y?: number;
  max_zoom?: number;
  tile_size?: number;
  paper_count?: number;
  url_template?: string;
  note?: string;
}

interface PaperHit {
  paper_id: string;
  title: string;
  year: number | null;
  cited_by_count: number;
  in_degree: number;
  out_degree: number;
  cluster_id: number;
  x: number;
  y: number;
}

interface Props {
  selectedPaperId: string | null;
  onSelectPaper: (paperId: string) => void;
}

const CitationMapView: React.FC<Props> = ({ onSelectPaper }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hits, setHits] = useState<PaperHit[] | null>(null);
  const [clickInfo, setClickInfo] = useState<{ x: number; y: number } | null>(null);

  // Load manifest
  useEffect(() => {
    let cancelled = false;
    fetch('/api/map/manifest')
      .then((r) => r.json())
      .then((m: Manifest) => {
        if (cancelled) return;
        setManifest(m);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to load map');
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Initialize Leaflet once we have the manifest
  useEffect(() => {
    if (!manifest || !manifest.available || !containerRef.current) return;
    let cleanup: (() => void) | null = null;

    (async () => {
      const L = (await import('leaflet')).default;
      // @ts-ignore - inject the Leaflet CSS once
      if (!document.querySelector('link[data-leaflet-css]')) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        link.setAttribute('data-leaflet-css', '1');
        document.head.appendChild(link);
      }

      const tileSize = manifest.tile_size || 256;
      const maxZoom = manifest.max_zoom ?? 6;

      const map = L.map(containerRef.current!, {
        crs: L.CRS.Simple,
        minZoom: 0,
        maxZoom,
        zoomControl: true,
        attributionControl: false,
        background: '#0a0e1a',
      } as any);

      mapRef.current = map;

      // Pixel size of the entire world at maxZoom
      const worldPixels = tileSize * Math.pow(2, maxZoom);
      const bounds = L.latLngBounds(
        map.unproject([0, worldPixels], maxZoom),
        map.unproject([worldPixels, 0], maxZoom),
      );
      map.fitBounds(bounds);
      map.setMaxBounds(bounds.pad(0.5));

      L.tileLayer('/data/tiles/{z}/{x}/{y}.png', {
        tileSize,
        minZoom: 0,
        maxZoom,
        noWrap: true,
        bounds,
      }).addTo(map);

      // Convert from screen click → world (x,y) coordinates used in SQLite
      const minX = manifest.min_x ?? -1;
      const maxX = manifest.max_x ?? 1;
      const minY = manifest.min_y ?? -1;
      const maxY = manifest.max_y ?? 1;
      const span = Math.max(maxX - minX, maxY - minY);

      const screenToWorld = (latlng: any) => {
        const point = map.project(latlng, maxZoom);
        const fx = point.x / worldPixels;
        const fy = point.y / worldPixels;
        return {
          wx: minX + fx * span,
          wy: maxY - fy * span,
        };
      };

      map.on('click', async (e: any) => {
        const { wx, wy } = screenToWorld(e.latlng);
        setClickInfo({ x: wx, y: wy });
        setHits(null);
        const zoom = map.getZoom();
        // Larger radius at lower zoom levels
        const r = span / Math.pow(2, zoom + 4);
        try {
          const res = await fetch(`/api/map/papers-at?cx=${wx}&cy=${wy}&r=${r}&limit=12`);
          const json = await res.json();
          setHits(json.papers || []);
        } catch {
          setHits([]);
        }
      });

      cleanup = () => {
        map.remove();
        mapRef.current = null;
      };
    })().catch((err) => {
      setError(err instanceof Error ? err.message : 'Failed to initialize map');
    });

    return () => {
      cleanup?.();
    };
  }, [manifest]);

  if (loading) return <GraphSkeleton />;
  if (error) return <ErrorState error={error} onRetry={() => window.location.reload()} />;

  if (!manifest?.available) {
    return (
      <div className="w-full h-full flex items-center justify-center p-10 text-center">
        <div className="max-w-lg space-y-4">
          <h2 className="text-xl text-white font-semibold">No tile map yet</h2>
          <p className="text-sm text-muted leading-relaxed">
            The map view needs precomputed tiles. Generate them with:
          </p>
          <pre className="text-xs text-left bg-black/40 border border-white/10 rounded-lg p-4 overflow-x-auto mono-text">
{`python scripts/citation_network/build_from_year_files.py \\
  --input-dir <path-to-year-files> --reset
python scripts/citation_network/compute_layout.py
python scripts/citation_network/render_tiles.py --max-zoom 6`}
          </pre>
          {manifest?.note && <p className="text-xs text-muted">{manifest.note}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative">
      <div className="absolute top-6 left-6 z-[400] pointer-events-none">
        <div className="bg-black/60 backdrop-blur-md border border-white/10 rounded-lg p-3 pointer-events-auto shadow-2xl">
          <div className="flex items-center gap-6">
            <div>
              <p className="text-[10px] text-muted uppercase tracking-widest mono-text mb-0.5">Total Papers</p>
              <p className="text-sm text-white font-medium mono-text">{manifest.paper_count?.toLocaleString() || '?'}</p>
            </div>
            <div className="w-px h-8 bg-white/10"></div>
            <div>
              <p className="text-[10px] text-muted uppercase tracking-widest mono-text mb-0.5">Mode</p>
              <p className="text-sm text-white font-medium mono-text">Map Tiles</p>
            </div>
          </div>
        </div>
      </div>

      <div ref={containerRef} className="absolute inset-0 bg-[#0a0e1a]" />

      {hits && (
        <div className="absolute right-6 bottom-6 z-[400] w-[360px] max-h-[60vh] overflow-y-auto bg-black/70 backdrop-blur-md border border-white/10 rounded-lg shadow-2xl">
          <div className="p-3 border-b border-white/10 flex items-center justify-between">
            <div>
              <p className="text-[10px] text-muted uppercase tracking-widest mono-text">Papers near click</p>
              {clickInfo && (
                <p className="text-[10px] text-muted mono-text mt-0.5">
                  ({clickInfo.x.toFixed(3)}, {clickInfo.y.toFixed(3)})
                </p>
              )}
            </div>
            <button
              onClick={() => { setHits(null); setClickInfo(null); }}
              className="text-xs text-muted hover:text-white px-2 py-1"
            >
              ✕
            </button>
          </div>
          {hits.length === 0 ? (
            <p className="p-4 text-xs text-muted">No papers in this area. Try clicking on a denser region or zoom in.</p>
          ) : (
            <ul className="divide-y divide-white/5">
              {hits.map((p) => (
                <li key={p.paper_id}>
                  <button
                    onClick={() => onSelectPaper(p.paper_id)}
                    className="w-full text-left px-3 py-2 hover:bg-white/5 transition"
                  >
                    <p className="text-xs text-white leading-snug line-clamp-2">{p.title || 'Untitled paper'}</p>
                    <p className="text-[10px] text-muted mono-text mt-1">
                      {p.year ?? '—'} · {p.cited_by_count?.toLocaleString() ?? 0} citations · cluster {p.cluster_id ?? '—'}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};

export default CitationMapView;
