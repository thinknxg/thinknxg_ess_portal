<script setup lang="ts">
import { computed, ref } from "vue";
import { useResource } from "@/composables/useResource";
import { CheckinAdmin } from "@/services/endpoints";
import { fmtDate, fmtTime } from "@/i18n";
import { addDays, isoToday } from "@/utils/format";
import PageHeader from "@/components/ui/PageHeader.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import AccessibleDialog from "@/components/ui/AccessibleDialog.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import EmptyState from "@/components/ui/EmptyState.vue";

const f = ref({ from_date: addDays(isoToday(), -7), to_date: isoToday(), decision: "", reason_code: "", risk: "" });
const params = computed(() => ({ ...f.value }));
const { data, loading } = useResource<any>(() => `ci:logs:${JSON.stringify(params.value)}`, () => CheckinAdmin.logs(params.value), { watch: [params] });
const codes = computed(() => {
  const m: Record<string, { allowed: number; denied: number }> = {};
  for (const r of data.value?.summary || []) { const k = r.reason_code || "?"; (m[k] ||= { allowed: 0, denied: 0 }); r.decision === "Allowed" ? (m[k].allowed += r.n) : (m[k].denied += r.n); }
  return Object.entries(m).sort((a, b) => (b[1].denied + b[1].allowed) - (a[1].denied + a[1].allowed));
});
const detail = ref<any>(null);
async function open(r: any) { detail.value = await CheckinAdmin.logDetail(r.name); }
const trace = computed(() => { try { return JSON.parse(detail.value?.policy_trace || "{}"); } catch { return {}; } });
const osm = (lat: number, lng: number) => `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=18/${lat}/${lng}`;
function csv() {
  const rows = data.value?.rows || [];
  const cols = ["server_time", "employee", "employee_name", "log_type", "decision", "reason_code", "message", "matched_location", "distance_m", "nearest_location", "nearest_distance_m", "accuracy", "latitude", "longitude", "shift_type", "risk_level", "risk_flags", "source", "ip_address", "checkin"];
  const esc = (v: any) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const body = [cols.join(","), ...rows.map((r: any) => cols.map((c) => esc(r[c])).join(","))].join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([body], { type: "text/csv" }));
  a.download = `checkin-audit-${f.value.from_date}-${f.value.to_date}.csv`;
  a.click();
}
</script>

<template>
  <div class="page">
    <PageHeader title="Check-in audit" subtitle="Every ESS portal check-in attempt: who, when, where, and the policy decision." back="/hr/checkin">
      <button class="btn" @click="csv" :disabled="!data?.rows?.length">Export CSV</button>
    </PageHeader>
    <div class="filters">
      <input type="date" class="input" v-model="f.from_date" aria-label="From" />
      <input type="date" class="input" v-model="f.to_date" :min="f.from_date" aria-label="To" />
      <select class="select" v-model="f.decision" aria-label="Decision"><option value="">Allowed and denied</option><option>Allowed</option><option>Denied</option></select>
      <select class="select" v-model="f.reason_code" aria-label="Reason"><option value="">Any reason</option><option v-for="[c] in codes" :key="c" :value="c">{{ c }}</option></select>
      <select class="select" v-model="f.risk" aria-label="Risk"><option value="">Any risk</option><option>High</option><option>Low</option><option>None</option></select>
    </div>
    <div class="chips" v-if="codes.length">
      <button v-for="[c, n] in codes" :key="c" class="chipbtn" :class="{ on: f.reason_code === c }" @click="f.reason_code = f.reason_code === c ? '' : c">{{ c }} <b class="num">{{ n.denied + n.allowed }}</b></button>
    </div>
    <section class="panel">
      <SkeletonLoader v-if="loading && !data" :lines="8" />
      <div class="table-wrap" v-else-if="data?.rows?.length">
        <table class="data"><thead><tr><th>Time</th><th>Employee</th><th>Punch</th><th>Decision</th><th>Location</th><th class="n">Accuracy</th><th>Risk</th></tr></thead>
          <tbody><tr v-for="r in data.rows" :key="r.name" class="click" tabindex="0" @click="open(r)" @keydown.enter="open(r)">
            <td class="small num">{{ fmtDate(r.server_time, { day: "numeric", month: "short" }) }} {{ fmtTime(r.server_time) }}</td>
            <td>{{ r.employee_name }}<br><span class="small muted">{{ r.employee }}</span></td>
            <td>{{ r.log_type }}</td>
            <td><StatusBadge :tone="r.decision === 'Allowed' ? 'ok' : 'bad'" :label="r.decision" /><br><span class="small muted">{{ r.reason_code }}</span></td>
            <td class="small">{{ r.matched_location || (r.nearest_location ? `${Math.round(r.nearest_distance_m)} m from ${r.nearest_location}` : "—") }}</td>
            <td class="n small">{{ r.accuracy != null ? `±${Math.round(r.accuracy)} m` : "—" }}</td>
            <td><StatusBadge v-if="r.risk_level && r.risk_level !== 'None'" :tone="r.risk_level === 'High' ? 'bad' : 'warn'" :label="r.risk_level" /></td></tr></tbody></table>
      </div>
      <EmptyState v-else title="No check-in attempts match these filters" icon="clock" />
    </section>

    <AccessibleDialog :open="!!detail" :title="detail ? `${detail.employee_name} · ${detail.log_type} · ${detail.decision}` : ''" wide @close="detail = null">
      <div v-if="detail" class="stack">
        <p v-if="detail.message"><strong>{{ detail.message }}</strong></p>
        <dl class="kv">
          <div><dt>Server time</dt><dd>{{ detail.server_time }}</dd></div><div><dt>Device time</dt><dd>{{ detail.client_time || "—" }}</dd></div>
          <div><dt>Source</dt><dd>{{ detail.source }}</dd></div><div><dt>User</dt><dd>{{ detail.user }}</dd></div>
          <div><dt>Coordinates</dt><dd><a v-if="detail.latitude" :href="osm(detail.latitude, detail.longitude)" target="_blank" rel="noopener">{{ detail.latitude }}, {{ detail.longitude }}</a><span v-else>—</span></dd></div>
          <div><dt>Accuracy</dt><dd>{{ detail.accuracy != null ? `±${detail.accuracy} m` : "—" }}</dd></div>
          <div><dt>Matched / nearest</dt><dd>{{ detail.matched_location || detail.nearest_location || "—" }}<template v-if="detail.distance_m || detail.nearest_distance_m"> ({{ Math.round(detail.distance_m || detail.nearest_distance_m) }} m)</template></dd></div>
          <div><dt>Shift</dt><dd>{{ detail.shift_type || "—" }}<template v-if="detail.window_open"> · {{ fmtTime(detail.window_open) }}–{{ fmtTime(detail.window_close) }}</template></dd></div>
          <div><dt>Risk</dt><dd>{{ detail.risk_level }}<template v-if="detail.risk_flags"> · {{ detail.risk_flags }}</template></dd></div>
          <div><dt>IP address</dt><dd>{{ detail.ip_address || "—" }}</dd></div>
          <div><dt>Employee Checkin</dt><dd><a v-if="detail.checkin" :href="`/app/employee-checkin/${detail.checkin}`">{{ detail.checkin }}</a><span v-else>Not created</span></dd></div>
          <div><dt>Override</dt><dd>{{ detail.policy_override || "—" }}</dd></div>
        </dl>
        <div><h3>Policy decision</h3><ol class="trace"><li v-for="(x, i) in trace.trace || []" :key="i">{{ x }}</li></ol></div>
        <div v-if="trace.candidates?.length"><h3>Locations considered</h3><ul class="small"><li v-for="c in trace.candidates" :key="c.name">{{ c.name }} · {{ c.radius }} m · {{ c.source }}</li></ul></div>
        <p class="small muted">{{ detail.user_agent }}</p>
      </div>
    </AccessibleDialog>
  </div>
</template>

<style scoped>
.filters { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; }
.chipbtn { border: 1px solid var(--line); background: var(--surface); border-radius: 16px; padding: 4px 10px; font-size: var(--fs-xs); cursor: pointer; }
.chipbtn.on { border-color: var(--brand); background: var(--brand-soft); }
.chipbtn b { margin-inline-start: 4px; }
tr.click { cursor: pointer; } tr.click:hover td { background: var(--surface-2); }
.kv { margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px 16px; }
dt { font-size: var(--fs-xs); color: var(--ink-3); } dd { margin: 0; overflow-wrap: anywhere; font-size: var(--fs-sm); }
.trace { padding-inline-start: 18px; margin: 6px 0; font-size: var(--fs-sm); display: flex; flex-direction: column; gap: 4px; }
h3 { font-size: var(--fs-sm); }
@media (max-width: 760px) { .filters { grid-template-columns: 1fr 1fr; } }
</style>
