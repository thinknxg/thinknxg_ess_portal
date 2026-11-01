<script setup lang="ts">
import { fmtDate } from "@/i18n";
import ShiftChip from "./ShiftChip.vue";
defineProps<{ days: any[]; limit?: number }>();
</script>

<template>
  <ul class="list up">
    <li v-for="d in days.slice(0, limit || 5)" :key="d.date">
      <span class="when"><span class="wd">{{ fmtDate(d.date, { weekday: "short" }) }}</span><span class="dn num">{{ fmtDate(d.date, { day: "2-digit", month: "short" }) }}</span></span>
      <span class="grow">
        <template v-if="d.shifts.length">
          <span v-for="s in d.shifts" :key="s.start_dt" class="sh"><ShiftChip :code="s.code" :color="s.color" size="sm" /> <span>{{ s.shift_type }}</span></span>
        </template>
        <span v-else-if="d.leave" class="muted">{{ d.leave.leave_type }}<template v-if="d.leave.status !== 'Approved'"> ({{ d.leave.status }})</template></span>
        <span v-else-if="d.holiday && !d.holiday.weekly_off" class="hol">{{ d.holiday.description }}</span>
        <span v-else-if="d.rest_day || d.holiday" class="muted">Rest day</span>
        <span v-else class="muted">No shift</span>
      </span>
      <span class="num small" v-if="d.shifts.length">{{ d.shifts[0].start }}–{{ d.shifts[d.shifts.length - 1].end }}</span>
    </li>
  </ul>
</template>

<style scoped>
.up li { gap: 14px; }
.when { display: flex; flex-direction: column; min-width: 54px; line-height: 1.2; }
.wd { font-size: var(--fs-xs); color: var(--ink-3); }
.dn { font-weight: 600; font-size: var(--fs-sm); }
.sh { display: inline-flex; align-items: center; gap: 6px; margin-inline-end: 10px; }
.hol { color: var(--saffron-ink); font-weight: 500; }
</style>
