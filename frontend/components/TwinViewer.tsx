"use client";

import { useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Grid, OrbitControls } from "@react-three/drei";
import {
  BAND_STROKE,
  type Detection,
  type MediaFile,
  type SeverityBand,
} from "@/lib/api";
import {
  DECK_HEIGHT,
  DECK_LENGTH,
  DECK_WIDTH,
  placeMarkers,
  type PlacedMarker,
} from "@/lib/placement";

/**
 * "Digital Twin v1" — a parametric structure with clickable defect markers.
 *
 * Per README D-003 this is deliberately not a photogrammetric reconstruction.
 * The geometry is generated in code rather than loaded from a GLB, so the
 * viewer needs no asset pipeline and cannot imply a fidelity it does not have.
 */

function Structure() {
  const concrete = "#9aa5b1";
  const dark = "#6b7684";
  const pierX = [-DECK_LENGTH / 3, DECK_LENGTH / 3];

  return (
    <group>
      {/* deck slab */}
      <mesh position={[0, DECK_HEIGHT, 0]} castShadow receiveShadow>
        <boxGeometry args={[DECK_LENGTH, 0.45, DECK_WIDTH]} />
        <meshStandardMaterial color={concrete} roughness={0.9} />
      </mesh>

      {/* parapets */}
      {[-1, 1].map((side) => (
        <mesh
          key={side}
          position={[0, DECK_HEIGHT + 0.55, (side * DECK_WIDTH) / 2 - side * 0.2]}
        >
          <boxGeometry args={[DECK_LENGTH, 0.65, 0.25]} />
          <meshStandardMaterial color={dark} roughness={0.85} />
        </mesh>
      ))}

      {/* longitudinal girders */}
      {[-1.6, 0, 1.6].map((z) => (
        <mesh key={z} position={[0, DECK_HEIGHT - 0.6, z]}>
          <boxGeometry args={[DECK_LENGTH * 0.98, 0.75, 0.5]} />
          <meshStandardMaterial color={dark} roughness={0.9} />
        </mesh>
      ))}

      {/* piers and pier caps */}
      {pierX.map((x) => (
        <group key={x}>
          <mesh position={[x, DECK_HEIGHT - 1.15, 0]}>
            <boxGeometry args={[1.8, 0.4, DECK_WIDTH * 0.9]} />
            <meshStandardMaterial color={concrete} roughness={0.9} />
          </mesh>
          {[-1.4, 1.4].map((z) => (
            <mesh key={z} position={[x, (DECK_HEIGHT - 1.35) / 2, z]}>
              <cylinderGeometry args={[0.42, 0.5, DECK_HEIGHT - 1.35, 20]} />
              <meshStandardMaterial color={concrete} roughness={0.9} />
            </mesh>
          ))}
        </group>
      ))}

      {/* abutments */}
      {[-DECK_LENGTH / 2, DECK_LENGTH / 2].map((x) => (
        <mesh key={x} position={[x, (DECK_HEIGHT - 0.4) / 2, 0]}>
          <boxGeometry args={[1.1, DECK_HEIGHT - 0.4, DECK_WIDTH]} />
          <meshStandardMaterial color={dark} roughness={0.95} />
        </mesh>
      ))}
    </group>
  );
}

function Marker({
  marker,
  selected,
  onSelect,
}: {
  marker: PlacedMarker;
  selected: boolean;
  onSelect: (m: PlacedMarker | null) => void;
}) {
  const [hovered, setHovered] = useState(false);
  const band = (marker.detection.severity_band ?? "low") as SeverityBand;
  const colour = BAND_STROKE[band];

  // Size carries severity as well as colour, so the worst findings read at a
  // glance and remain distinguishable to a colour-blind viewer.
  const score = marker.detection.severity_score ?? 0;
  const radius = 0.16 + Math.min(0.34, score * 14);
  const active = selected || hovered;

  return (
    <group position={marker.position}>
      <mesh
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          document.body.style.cursor = "auto";
        }}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(selected ? null : marker);
        }}
      >
        <sphereGeometry args={[radius, 18, 18]} />
        <meshStandardMaterial
          color={colour}
          emissive={colour}
          emissiveIntensity={active ? 0.9 : 0.35}
          roughness={0.35}
        />
      </mesh>
      {active && (
        <mesh>
          <sphereGeometry args={[radius * 1.85, 18, 18]} />
          <meshBasicMaterial color={colour} transparent opacity={0.18} />
        </mesh>
      )}
    </group>
  );
}

interface Props {
  media: MediaFile[];
  detections: Detection[];
}

export function TwinViewer({ media, detections }: Props) {
  const markers = useMemo(
    () => placeMarkers(media, detections),
    [media, detections],
  );
  const [selected, setSelected] = useState<PlacedMarker | null>(null);

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="relative h-[460px] bg-gradient-to-b from-slate-100 to-slate-200 dark:from-slate-900 dark:to-slate-950">
        {/*
          The canvas sizes itself from a ResizeObserver on this container.
          While the document is hidden (background tab, headless capture) the
          observer reports nothing and the canvas stays at its 300x150 default
          — the container is still laid out correctly, so it fills in as soon
          as the page is actually displayed.
        */}
        <Canvas
          shadows
          camera={{ position: [18, 12, 18], fov: 42 }}
          onPointerMissed={() => setSelected(null)}
        >
          <ambientLight intensity={0.7} />
          <directionalLight position={[12, 18, 10]} intensity={1.5} castShadow />
          <directionalLight position={[-10, 6, -8]} intensity={0.4} />
          <Structure />
          {markers.map((m) => (
            <Marker
              key={m.detection.id}
              marker={m}
              selected={selected?.detection.id === m.detection.id}
              onSelect={setSelected}
            />
          ))}
          <Grid
            args={[60, 60]}
            position={[0, -0.01, 0]}
            cellColor="#c3cbd6"
            sectionColor="#93a1b3"
            fadeDistance={55}
            infiniteGrid
          />
          <OrbitControls
            enablePan
            minDistance={8}
            maxDistance={60}
            maxPolarAngle={Math.PI / 2.05}
            target={[0, DECK_HEIGHT * 0.6, 0]}
          />
        </Canvas>

        {markers.length === 0 && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <p className="rounded-lg bg-white/85 px-4 py-2 text-sm text-slate-600 dark:bg-slate-900/85 dark:text-slate-300">
              No detections to place
            </p>
          </div>
        )}

        {selected && (
          <div className="absolute bottom-3 left-3 right-3 rounded-lg border border-slate-200 bg-white/95 p-3 shadow-lg backdrop-blur dark:border-slate-700 dark:bg-slate-900/95 sm:right-auto sm:max-w-sm">
            <div className="flex items-center gap-2">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{
                  background:
                    BAND_STROKE[
                      (selected.detection.severity_band ?? "low") as SeverityBand
                    ],
                }}
              />
              <p className="text-sm font-medium capitalize">
                {selected.detection.defect_class.replace("_", " ")} ·{" "}
                {selected.detection.severity_band}
              </p>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="ml-auto text-xs text-slate-400 hover:text-slate-600"
              >
                close
              </button>
            </div>
            <p className="mt-1.5 truncate text-xs text-slate-500">
              {selected.media.original_filename}
              {selected.detection.frame_index !== null &&
                ` · frame ${selected.detection.frame_index}`}
            </p>
            <p className="mt-1 font-mono text-[11px] text-slate-600 dark:text-slate-400">
              {selected.detection.normalized_area?.toFixed(4)} ×{" "}
              {selected.detection.confidence.toFixed(3)} ×{" "}
              {selected.detection.class_weight?.toFixed(1)} ={" "}
              {selected.detection.severity_score?.toFixed(5)}
            </p>
          </div>
        )}
      </div>

      <div className="border-t border-slate-200 px-4 py-3 dark:border-slate-800">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <p className="text-xs font-medium text-slate-600 dark:text-slate-400">
            {markers.length} marker{markers.length === 1 ? "" : "s"}
          </p>
          {(["critical", "high", "medium", "low"] as SeverityBand[]).map((b) => (
            <span key={b} className="flex items-center gap-1.5 text-xs">
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: BAND_STROKE[b] }}
              />
              <span className="capitalize text-slate-500">{b}</span>
            </span>
          ))}
          <span className="text-xs text-slate-400">
            drag to orbit · scroll to zoom · click a marker
          </span>
        </div>

        <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
          <strong>Illustrative placement, not a survey.</strong> The structure is
          a generic parametric model, not this asset. Marker positions are
          derived from capture order along the span and the detection&apos;s
          position within its frame — nothing in the pipeline recovers real
          3D coordinates. If the imagery was not captured in span order, the
          along-span axis is meaningless. Use the image overlays above for
          anything positional.
        </p>
      </div>
    </div>
  );
}
