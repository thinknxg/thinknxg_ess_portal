<script setup lang="ts">
const props = defineProps<{ value: number; max: number; label: string; detail?: string }>();
const pct = () => (props.max > 0 ? Math.min(100, Math.max(0, (props.value / props.max) * 100)) : 0);
</script>

<template>
  <div class="m">
    <div class="spread"><span class="l">{{ label }}</span><span class="num v">{{ detail }}</span></div>
    <div class="track" role="meter" :aria-valuenow="value" :aria-valuemin="0" :aria-valuemax="max" :aria-label="label">
      <span :style="{ width: pct() + '%' }" :class="{ low: pct() < 20 }" />
    </div>
  </div>
</template>

<style scoped>
.m { display: flex; flex-direction: column; gap: 6px; }
.l { font-size: var(--fs-sm); font-weight: 500; }
.v { font-size: var(--fs-sm); color: var(--ink-2); }
.track { height: 6px; border-radius: 3px; background: var(--surface-2); overflow: hidden; }
.track span { display: block; height: 100%; background: var(--brand); border-radius: 3px; }
.track span.low { background: var(--saffron); }
</style>
