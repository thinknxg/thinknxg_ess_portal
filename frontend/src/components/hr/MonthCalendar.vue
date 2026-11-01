<script setup lang="ts">
/** Generic month grid used by the attendance and leave calendars. Week starts Sunday (GCC). */
import { computed } from "vue";
import { lang } from "@/i18n";

export interface DayCell { date: string; tone?: string; color?: string; label?: string; marks?: { tone: string; text: string }[]; muted?: boolean }
const props = defineProps<{ year: number; month: number; cells: Record<string, DayCell>; selected?: string | null; weekend?: number[] }>();
const emit = defineEmits<{ select: [date: string]; prev: []; next: [] }>();

const title = computed(() => new Date(props.year, props.month - 1, 1).toLocaleDateString(lang.value === "ar" ? "ar-OM" : "en-GB", { month: "long", year: "numeric" }));
const weekdays = computed(() => [...Array(7)].map((_, i) => new Date(2023, 0, 1 + i).toLocaleDateString(lang.value === "ar" ? "ar-OM" : "en-GB", { weekday: "short" })));
const grid = computed(() => {
  const first = new Date(props.year, props.month - 1, 1);
  const days = new Date(props.year, props.month, 0).getDate();
  const out: (string | null)[] = Array(first.getDay()).fill(null);
  for (let d = 1; d <= days; d++) out.push(`${props.year}-${String(props.month).padStart(2, "0")}-${String(d).padStart(2, "0")}`);
  while (out.length % 7) out.push(null);
  return out;
});
const today = new Date().toISOString().slice(0, 10);
</script>

<template>
  <div class="cal">
    <div class="head">
      <button class="btn ghost icon" @click="emit('prev')" aria-label="Previous month">‹</button>
      <h2 aria-live="polite">{{ title }}</h2>
      <button class="btn ghost icon" @click="emit('next')" aria-label="Next month">›</button>
    </div>
    <div class="grid" role="grid" :aria-label="title">
      <div v-for="w in weekdays" :key="w" class="wd" role="columnheader">{{ w }}</div>
      <template v-for="(d, i) in grid" :key="i">
        <div v-if="!d" class="cell blank" aria-hidden="true" />
        <button v-else class="cell" role="gridcell" :class="[cells[d]?.tone, { sel: selected === d, today: d === today, wknd: (weekend || [5, 6]).includes(i % 7), muted: cells[d]?.muted, custom: cells[d]?.color }]"
                :style="cells[d]?.color ? { '--cc': cells[d]?.color } : undefined"
                :aria-selected="selected === d" :aria-label="`${d} ${cells[d]?.label || ''}`" @click="emit('select', d)">
          <span class="dn num">{{ +d.slice(8) }}</span>
          <span v-if="cells[d]?.label" class="lbl">{{ cells[d]?.label }}</span>
          <span class="marks"><i v-for="(m, j) in (cells[d]?.marks || []).slice(0, 3)" :key="j" :class="m.tone" :title="m.text" /></span>
        </button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.head h2 { font-size: var(--fs-md); }
[dir="rtl"] .head .btn { transform: scaleX(-1); }
.grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }
.wd { font-size: var(--fs-xs); color: var(--ink-3); text-align: center; padding: 4px 0; }
.cell { position: relative; min-height: 64px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); padding: 6px; display: flex; flex-direction: column; align-items: flex-start; gap: 2px; cursor: pointer; text-align: start; }
.cell.blank { border: 0; background: none; cursor: default; }
.cell.wknd { background: var(--surface-2); }
.cell.today { border-color: var(--brand); box-shadow: inset 0 0 0 1px var(--brand); }
.cell.sel { outline: 2px solid var(--focus); }
.cell.muted { opacity: .55; }
.dn { font-size: var(--fs-sm); font-weight: 600; }
.lbl { font-size: 11px; line-height: 1.2; color: var(--ink-2); overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.marks { position: absolute; bottom: 6px; inset-inline-end: 6px; display: flex; gap: 3px; }
.marks i { width: 7px; height: 7px; border-radius: 50%; }
.ok { border-inline-start: 3px solid var(--ok); } .marks .ok { background: var(--ok); border: 0; }
.warn { border-inline-start: 3px solid var(--saffron); } .marks .warn { background: var(--saffron); border: 0; }
.bad { border-inline-start: 3px solid var(--pom); } .marks .bad { background: var(--pom); border: 0; }
.info { border-inline-start: 3px solid var(--info); } .marks .info { background: var(--info); border: 0; }
.brand { border-inline-start: 3px solid var(--brand); } .marks .brand { background: var(--brand); border: 0; }
.cell.custom { border-inline-start: 3px solid var(--cc); background: color-mix(in srgb, var(--cc) 7%, var(--surface)); }
@media (max-width: 640px) { .cell { min-height: 46px; padding: 4px; } .lbl { display: none; } }
</style>
