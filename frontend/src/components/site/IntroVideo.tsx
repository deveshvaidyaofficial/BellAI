"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { VolumeX } from "lucide-react";
import { useEffect, useRef, useState } from "react";

/** How far the film shrinks by the end of the scroll range. Subtler on phones. */
const END_SCALE = { desktop: 0.86, mobile: 0.92 };

/**
 * The 60-second intro film. Plays muted while at least half of it is on screen (never with
 * sound, never when reduced motion is on) and keeps the native controls. Once the viewer
 * pauses, seeks or unmutes, scrolling no longer starts or stops it.
 *
 * Scroll-linked: it opens large and eases down in scale as the page scrolls, while its
 * shadow softens. Transform and opacity only; reduced motion pins it static in CSS.
 */
export function IntroVideo() {
  const ref = useRef<HTMLVideoElement>(null);
  const [muted, setMuted] = useState(true);
  const [playing, setPlaying] = useState(false);
  const touched = useRef(false);
  const autoPaused = useRef(false);
  const stage = useRef<HTMLDivElement>(null);
  const range = useRef(520);
  const endScale = useRef(END_SCALE.desktop);

  const { scrollY } = useScroll();
  const progress = useTransform(scrollY, (y) => Math.min(1, Math.max(0, y / range.current)));
  const scale = useTransform(progress, (p) => 1 - (1 - endScale.current) * easeOut(p));
  const glow = useTransform(progress, [0, 1], [1, 0.3]);

  useEffect(() => {
    const mobile = window.matchMedia("(max-width: 760px)");
    const measure = () => {
      endScale.current = mobile.matches ? END_SCALE.mobile : END_SCALE.desktop;
      const h = stage.current?.offsetHeight ?? 520;
      range.current = Math.max(h * 0.85, window.innerHeight * 0.45);
    };
    measure();
    mobile.addEventListener("change", measure);
    window.addEventListener("resize", measure);
    return () => {
      mobile.removeEventListener("change", measure);
      window.removeEventListener("resize", measure);
    };
  }, []);

  useEffect(() => {
    const video = ref.current;
    if (!video) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    let io: IntersectionObserver | null = null;

    const autoPause = () => {
      if (!video.paused && video.muted) {
        autoPaused.current = true;
        video.pause();
      }
    };
    const start = () => {
      io = new IntersectionObserver(
        ([entry]) => {
          if (touched.current) return;
          if (entry.intersectionRatio >= 0.5) {
            video.muted = true;
            video.play().catch(() => {});
          } else {
            autoPause();
          }
        },
        { threshold: [0, 0.5] },
      );
      io.observe(video);
    };
    const stop = () => {
      io?.disconnect();
      io = null;
      autoPause();
    };
    const onChange = () => (reduce.matches ? stop() : start());

    if (!reduce.matches) start();
    reduce.addEventListener("change", onChange);
    return () => {
      reduce.removeEventListener("change", onChange);
      io?.disconnect();
    };
  }, []);

  const unmute = () => {
    const video = ref.current;
    if (!video) return;
    touched.current = true;
    video.muted = false;
    if (video.volume === 0) video.volume = 1;
    if (video.ended || video.currentTime > video.duration - 0.5) video.currentTime = 0;
    video.play().catch(() => {});
    video.focus();
  };

  return (
    <motion.div ref={stage} className="iv-stage" style={{ scale }}>
      <motion.div className="iv-glow" aria-hidden="true" style={{ opacity: glow }} />
      <div className="iv-frame">
      <video
        ref={ref}
        className="iv-video"
        poster="/videos/intro-poster.jpg"
        controls
        playsInline
        muted
        preload="metadata"
        aria-label="BellAI intro video, 60 seconds. All words appear on screen."
        onPlay={() => setPlaying(true)}
        onPause={() => {
          setPlaying(false);
          if (!autoPaused.current) touched.current = true;
          autoPaused.current = false;
        }}
        onVolumeChange={(e) => {
          const v = e.currentTarget;
          setMuted(v.muted || v.volume === 0);
          if (!v.muted) touched.current = true;
        }}
        onSeeking={() => { touched.current = true; }}
      >
        <source src="/videos/intro.webm" type='video/webm; codecs="vp9, opus"' />
        <source src="/videos/intro.mp4" type='video/mp4; codecs="avc1.640028, mp4a.40.2"' />
        Your browser can’t play this video. <a href="/videos/intro.mp4">Download it</a> instead.
      </video>
      {playing && muted && (
        <button type="button" className="iv-unmute" onClick={unmute}>
          <VolumeX size={16} aria-hidden="true" />
          Turn on sound
        </button>
      )}
      </div>
    </motion.div>
  );
}

function easeOut(p: number) {
  return 1 - (1 - p) * (1 - p);
}
