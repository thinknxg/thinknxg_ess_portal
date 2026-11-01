<script setup lang="ts">
import { computed, ref } from "vue";
import { useResource } from "@/composables/useResource";
import { Team } from "@/services/endpoints";
import { useApprovalQueue } from "@/composables/hr";
import { useSession } from "@/stores/session";
import { fmtDate, t } from "@/i18n";
import PageHeader from "@/components/ui/PageHeader.vue";
import Avatar from "@/components/ui/Avatar.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import SegmentTabs from "@/components/ui/SegmentTabs.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";
import EmptyState from "@/components/ui/EmptyState.vue";

const s = useSession();
const { data, loading, error, reload } = useResource<any>(() => "team:overview", () => Team.overview(), { staleMs: 20_000 });
const { data: exc } = useResource<any>(() => "team:exc", () => Team.exceptions(7));
const { items: approvals } = useApprovalQueue();
const filter = ref("all");
const members = computed(() => (data.value?.members || []).filter((m: any) => filter.value === "all" || m.today === filter.value));
const ORDER = ["Checked In", "Not Checked In", "On Leave", "Checked Out"];
const tabs = computed(() => [{ value: "all", label: t("All"), count: data.value?.members.length },
  ...ORDER.filter((k) => data.value?.counts[k]).map((k) => ({ value: k, label: t(k === "On Leave" ? "On leave" : k), count: data.value.counts[k] }))]);
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Team overview')" subtitle="Your direct and indirect reports, as of right now.">
      <RouterLink v-if="s.can('planner')" to="/team/roster" class="btn">Roster planner</RouterLink>
      <RouterLink to="/team/calendar" class="btn">{{ t("Leave calendar") }}</RouterLink>
      <RouterLink to="/team/approvals" class="btn primary">{{ t("Approvals") }} <span class="num" v-if="approvals.length">({{ approvals.length }})</span></RouterLink>
    </PageHeader>
    <ErrorState :error="error" @retry="reload" />
    <SkeletonLoader v-if="loading && !data" :lines="8" />
    <div class="cols" v-if="data">
      <section class="panel">
        <SegmentTabs v-model="filter" :tabs="tabs" label="Filter by status today" />
        <ul class="list" v-if="members.length">
          <li v-for="m in members" :key="m.name"><RouterLink :to="`/team/member/${m.name}`" class="rowlink">
            <Avatar :name="m.employee_name" :image="m.image" :size="34" />
            <span class="grow"><span class="title">{{ m.employee_name }}</span><br><span class="small muted">{{ m.designation }}</span></span>
            <span class="small muted num" v-if="m.first_seen">{{ m.first_seen }}</span>
            <StatusBadge :status="m.today" :label="m.leave_type || t(m.today === 'On Leave' ? 'On leave' : m.today)" />
          </RouterLink></li>
        </ul>
        <EmptyState v-else title="No one in this group" icon="users" />
      </section>
      <aside class="stack">
        <section class="panel tight">
          <header><h2>Away in the next two weeks</h2></header>
          <ul class="list" v-if="data.upcoming_leave.length"><li v-for="(u, i) in data.upcoming_leave" :key="i"><span class="grow">{{ u.employee_name }}<br><span class="small muted">{{ u.leave_type }}</span></span><span class="small num">{{ fmtDate(u.from_date, { day: "numeric", month: "short" }) }}–{{ fmtDate(u.to_date, { day: "numeric", month: "short" }) }}</span></li></ul>
          <p v-else class="muted small">No approved leave coming up.</p>
        </section>
        <section class="panel tight" v-if="exc">
          <header><h2>Attendance exceptions, last 7 days</h2></header>
          <ul class="list">
            <li v-for="(m, i) in exc.missing_punch" :key="'m' + i"><span class="grow">{{ m.employee_name }}</span><StatusBadge status="Missing" :label="`${t('Missing punch')} · ${fmtDate(m.d, { day: 'numeric', month: 'short' })}`" /></li>
            <li v-for="(a, i) in exc.absent" :key="'a' + i"><span class="grow">{{ a.employee_name }}</span><StatusBadge status="Absent" :label="`${t('Absent')} · ${fmtDate(a.attendance_date, { day: 'numeric', month: 'short' })}`" /></li>
            <li v-for="(l, i) in exc.late.slice(0, 8)" :key="'l' + i"><span class="grow">{{ l.employee_name }}</span><StatusBadge status="Late" :label="`${t('Late')} · ${fmtDate(l.attendance_date, { day: 'numeric', month: 'short' })}`" /></li>
          </ul>
          <p class="muted small" v-if="!exc.missing_punch.length && !exc.absent.length && !exc.late.length">No exceptions this week.</p>
        </section>
        <section class="panel tight" v-if="exc?.denied?.length || exc?.risk?.length">
          <header><h2>Portal check-in problems, last 7 days</h2></header>
          <ul class="list">
            <li v-for="(d, i) in exc.denied.slice(0, 8)" :key="'d' + i"><span class="grow">{{ d.employee_name }}<br><span class="small muted">{{ d.message }}</span></span>
              <StatusBadge status="Rejected" :label="fmtDate(d.server_time, { day: 'numeric', month: 'short' })" /></li>
            <li v-for="(r, i) in exc.risk.slice(0, 5)" :key="'r' + i"><span class="grow">{{ r.employee_name }}<br><span class="small muted">{{ r.risk_flags }}</span></span>
              <StatusBadge :tone="r.risk_level === 'High' ? 'bad' : 'warn'" :label="`${r.risk_level} risk`" /></li>
          </ul>
        </section>
      </aside>
    </div>
  </div>
</template>
