<script setup lang="ts">
/** Accessible SVG bar chart (stacked optional). Data arrives pre-aggregated from the server. */
import { computed } from "vue";
const props = defineProps<{ labels: string[]; series: { name: string; values: (number | null)[]; color: string }[]; stacked?: boolean; height?: number; title: string }>();
const H = computed(() => props.height || 180);
const max = computed(() => {
  const vals = props.labels.map((_, i) => props.stacked
    ? props.series.reduce((a, s) => a + (s.values[i] || 0), 0)
    : Math.max(...props.series.map((s) => s.values[i] || 0)));
  return Math.max(1, ...vals);
});
const nice = computed(() => { const m = max.value; const p = Math.pow(10, Math.floor(Math.log10(m))); return Math.ceil(m / p) * p; });
const ticks = computed(() => [0, 0.5, 1].map((f) => Math.round(nice.value * f)));
</script>

<template>
  <figure class="bc">
    <svg :viewBox="`0 0 ${labels.length * 48 + 36} ${H + 26}`" preserveAspectRatio="none" role="img" :aria-label="title" class="svg">
      <g v-for="tk in ticks" :key="tk">
        <line x1="32" :x2="labels.length * 48 + 36" :y1="H - (tk / nice) * H + 4" :y2="H - (tk / nice) * H + 4" class="grid" />
        <text x="26" :y="H - (tk / nice) * H + 8" class="tick" text-anchor="end">{{ tk }}</text>
      </g>
      <g v-for="(l, i) in labels" :key="l">
        <template v-if="stacked">
          <rect v-for="(s, j) in series" :key="s.name" :x="40 + i * 48" :width="28"
                :y="H + 4 - (series.slice(0, j + 1).reduce((a, x) => a + (x.values[i] || 0), 0) / nice) * H"
                :height="((s.values[i] || 0) / nice) * H" :fill="s.color" rx="2" />
        </template>
        <template v-else>
          <rect v-for="(s, j) in series" :key="s.name" :x="40 + i * 48 + j * (30 / series.length)" :width="Math.max(30 / series.length - 2, 4)"
                :y="H + 4 - ((s.values[i] || 0) / nice) * H" :height="((s.values[i] || 0) / nice) * H" :fill="s.color" rx="2" />
        </template>
        <text :x="54 + i * 48" :y="H + 22" class="tick" text-anchor="middle">{{ l }}</text>
      </g>
    </svg>
    <figcaption class="legend small">
      <span v-for="s in series" :key="s.name"><i :style="{ background: s.color }" />{{ s.name }}</span>
    </figcaption>
    <table class="sr-only">
      <caption>{{ title }}</caption>
      <tr><th>Period</th><th v-for="s in series" :key="s.name">{{ s.name }}</th></tr>
      <tr v-for="(l, i) in labels" :key="l"><td>{{ l }}</td><td v-for="s in series" :key="s.name">{{ s.values[i] ?? "suppressed" }}</td></tr>
    </table>
  </figure>
</template>

<style scoped>
.bc { margin: 0; }
.svg { width: 100%; height: auto; max-height: 240px; overflow: visible; }
.grid { stroke: var(--line); stroke-width: 1; }
.tick { font-size: 10px; fill: var(--ink-3); font-family: var(--font); }
.legend { display: flex; gap: 14px; flex-wrap: wrap; color: var(--ink-2); margin-top: 6px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-inline-end: 6px; vertical-align: -1px; }
</style>
