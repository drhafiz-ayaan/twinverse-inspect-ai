"use client";

import { useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { ContactShadows, Grid, Html, OrbitControls } from "@react-three/drei";
import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";
import type { Group, Mesh } from "three";
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
 * The geometry is generated in code rather than loaded from a GLB, so there is
 * no asset pipeline and the viewer cannot imply a fidelity it does not have.
 */

function Structure() {
  const concrete = "#8d99ab";
  const dark = "#5b6879";
  const pierX = [-DECK_LENGTH / 3, DECK_LENGTH / 3];

  return (
    <group>
      <mesh position={[0, DECK_HEIGHT, 0]} castShadow receiveShadow>
        <boxGeometry args={[DECK_LENGTH, 0.45, DECK_WIDTH]} />
        <meshStandardMaterial color={concrete} roughness={0.92} metalness={0.05} />
      </mesh>

      {[-1, 1].map((side) => (
        <mesh
          key={side}
          castShadow
          position={[0, DECK_HEIGHT + 0.55, (side * DECK_WIDTH) / 2 - side * 0.2]}
        >
          <boxGeometry args={[DECK_LENGTH, 0.65, 0.25]} />
          <meshStandardMaterial color={dark} roughness={0.85} />
        </mesh>
      ))}

      {[-1.6, 0, 1.6].map((z) => (
        <mesh key={z} castShadow position={[0, DECK_HEIGHT - 0.6, z]}>
          <boxGeometry args={[DECK_LENGTH * 0.98, 0.75, 0.5]} />
          <meshStandardMaterial color={dark} roughness={0.9} />
        </mesh>
      ))}

      {pierX.map((x) => (
        <group key={x}>
          <mesh castShadow position={[x, DECK_HEIGHT - 1.15, 0]}>
            <boxGeometry args={[1.8, 0.4, DECK_WIDTH * 0.9]} />
            <meshStandardMaterial color={concrete} roughness={0.9} />
          </mesh>
          {[-1.4, 1.4].map((z) => (
            <mesh key={z} castShadow position={[x, (DECK_HEIGHT - 1.35) / 2, z]}>
              <cylinderGeometry args={[0.42, 0.5, DECK_HEIGHT - 1.35, 24]} />
              <meshStandardMaterial color={concrete} roughness={0.9} />
            </mesh>
          ))}
        </group>
      ))}

      {[-DECK_LENGTH / 2, DECK_LENGTH / 2].map((x) => (
        <mesh key={x} castShadow position={[x, (DECK_HEIGHT - 0.4) / 2, 0]}>
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
  const group = useRef<Group>(null);
  const halo = useRef<Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const band = (marker.detection.severity_band ?? "low") as SeverityBand;
  const colour = BAND_STROKE[band];
  const score = marker.detection.severity_score ?? 0;
  // Size carries severity alongside colour, so the worst findings read at a
  // glance and stay distinguishable without relying on hue alone.
  const radius = 0.15 + Math.min(0.32, score * 13);
  const active = selected || hovered;

  // Phase offset from the marker id keeps the field from pulsing in unison,
  // which would look like a UI animation rather than distinct findings.
  const phase = useMemo(
    () => (parseInt(marker.detection.id.slice(0, 8), 16) % 1000) / 160,
    [marker.detection.id],
  );

  useFrame(({ clock }) => {
    const t = clock.elapsedTime + phase;
    if (group.current) group.current.position.y = marker.position[1] + Math.sin(t * 1.4) * 0.07;
    if (halo.current) {
      const s = 1.5 + Math.sin(t * 2.1) * 0.28;
      halo.current.scale.setScalar(active ? s * 1.35 : s);
      const mat = halo.current.material as { opacity: number };
      mat.opacity = (active ? 0.3 : 0.14) * (1 - (s - 1.2) * 0.5);
    }
  });

  return (
    <group ref={group} position={marker.position}>
      <mesh ref={halo}>
        <sphereGeometry args={[radius, 20, 20]} />
        <meshBasicMaterial color={colour} transparent opacity={0.16} depthWrite={false} />
      </mesh>

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
        <sphereGeometry args={[radius, 24, 24]} />
        <meshStandardMaterial
          color={colour}
          emissive={colour}
          emissiveIntensity={active ? 2.6 : 1.4}
          roughness={0.3}
          toneMapped={false}
        />
      </mesh>

      {active && (
        <Html center distanceFactor={16} style={{ pointerEvents: "none" }}>
          <div
            className="whitespace-nowrap rounded-md px-2 py-1 text-[11px] font-semibold backdrop-blur"
            style={{
              color: colour,
              background: "rgba(7,11,20,0.85)",
              boxShadow: `0 0 0 1px ${colour}66`,
            }}
          >
            {marker.detection.severity_score?.toFixed(5)}
          </div>
        </Html>
      )}
    </group>
  );
}

interface Props {
  media: MediaFile[];
  detections: Detection[];
}

export function TwinViewer({ media, detections }: Props) {
  const markers = useMemo(() => placeMarkers(media, detections), [media, detections]);
  const [selected, setSelected] = useState<PlacedMarker | null>(null);

  return (
    <div className="glass overflow-hidden">
      <div className="relative h-[520px]">
        {/*
          The canvas sizes itself from a ResizeObserver on this container.
          While the document is hidden (background tab, headless capture) the
          observer reports nothing and the canvas keeps its 300x150 default —
          the container is laid out correctly, so it fills in once displayed.
        */}
        <Canvas
          shadows
          dpr={[1, 2]}
          camera={{ position: [19, 13, 19], fov: 40 }}
          onPointerMissed={() => setSelected(null)}
          gl={{ antialias: true }}
        >
          <color attach="background" args={["#070b14"]} />
          <fog attach="fog" args={["#070b14", 34, 78]} />

          <ambientLight intensity={0.45} />
          <hemisphereLight args={["#7dd3fc", "#0b1220", 0.6]} />
          <directionalLight
            position={[14, 20, 11]}
            intensity={1.7}
            castShadow
            shadow-mapSize={[1024, 1024]}
          />
          <directionalLight position={[-12, 7, -9]} intensity={0.5} color="#6366f1" />

          <Structure />

          {markers.map((m) => (
            <Marker
              key={m.detection.id}
              marker={m}
              selected={selected?.detection.id === m.detection.id}
              onSelect={setSelected}
            />
          ))}

          <ContactShadows
            position={[0, 0.01, 0]}
            opacity={0.5}
            scale={46}
            blur={2.4}
            far={12}
          />
          <Grid
            args={[70, 70]}
            position={[0, 0, 0]}
            cellColor="#1b2942"
            sectionColor="#26527a"
            cellThickness={0.6}
            sectionThickness={1}
            fadeDistance={62}
            infiniteGrid
          />

          <OrbitControls
            enablePan
            autoRotate={!selected}
            autoRotateSpeed={0.35}
            minDistance={9}
            maxDistance={62}
            maxPolarAngle={Math.PI / 2.05}
            target={[0, DECK_HEIGHT * 0.6, 0]}
          />

          {/* Bloom makes emissive markers glow through the structure's shadow
              side. Threshold is high so only the markers bloom, never concrete. */}
          <EffectComposer>
            <Bloom intensity={0.9} luminanceThreshold={0.75} luminanceSmoothing={0.3} mipmapBlur />
            <Vignette eskil={false} offset={0.25} darkness={0.75} />
          </EffectComposer>
        </Canvas>

        {markers.length === 0 && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <p className="rounded-lg bg-black/70 px-4 py-2 text-sm text-[var(--text-1)] backdrop-blur">
              No detections to place
            </p>
          </div>
        )}

        {selected && (
          <div className="glass absolute bottom-3 left-3 right-3 p-3 sm:right-auto sm:max-w-sm">
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
                className="ml-auto text-xs text-[var(--text-2)] transition hover:text-[var(--text-0)]"
              >
                close
              </button>
            </div>
            <p className="mt-1.5 truncate text-[11px] text-[var(--text-2)]">
              {selected.media.original_filename}
              {selected.detection.frame_index !== null &&
                ` · frame ${selected.detection.frame_index}`}
            </p>
            <p className="mt-1 font-mono text-[10.5px] text-cyan-200/90">
              {selected.detection.normalized_area?.toFixed(4)} ×{" "}
              {selected.detection.confidence.toFixed(3)} ×{" "}
              {selected.detection.class_weight?.toFixed(1)} ={" "}
              {selected.detection.severity_score?.toFixed(5)}
            </p>
          </div>
        )}
      </div>

      <div className="border-t border-white/5 px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <p className="text-xs font-medium text-[var(--text-1)]">
            {markers.length} marker{markers.length === 1 ? "" : "s"}
          </p>
          {(["critical", "high", "medium", "low"] as SeverityBand[]).map((b) => (
            <span key={b} className="flex items-center gap-1.5 text-[11px]">
              <span
                className="h-2 w-2 rounded-full"
                style={{
                  background: BAND_STROKE[b],
                  boxShadow: `0 0 8px 1px ${BAND_STROKE[b]}88`,
                }}
              />
              <span className="capitalize text-[var(--text-2)]">{b}</span>
            </span>
          ))}
          <span className="text-[11px] text-[var(--text-2)]">
            drag to orbit · scroll to zoom · click a marker
          </span>
        </div>

        <p className="mt-3 rounded-lg border-l-2 border-amber-400/50 bg-amber-400/[0.06] px-3 py-2 text-[11px] leading-relaxed text-amber-200/90">
          <strong>Illustrative placement, not a survey.</strong> The structure
          is a generic parametric model, not this asset. Marker positions come
          from capture order along the span and the detection&apos;s position
          within its frame — nothing in the pipeline recovers real 3D
          coordinates. If the imagery was not captured in span order, the
          along-span axis is meaningless. Use the image overlays below for
          anything positional.
        </p>
      </div>
    </div>
  );
}
