<script setup lang="ts">
import { useRoute } from "vue-router";
import { useResource } from "@/composables/useResource";
import { Team } from "@/services/endpoints";
import { fmtDate, t } from "@/i18n";
import PageHeader from "@/components/ui/PageHeader.vue";
import Avatar from "@/components/ui/Avatar.vue";
import Meter from "@/components/hr/Meter.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";

const route = useRoute();
const emp = String(route.params.employee);
const { data: m, loading, error, reload } = useResource<any>(() => `team:m:${emp}`, () => Team.member(emp));
</script>

<template>
  <div class="page">
    <ErrorState :error="error" @retry="reload" />
    <SkeletonLoader v-if="loading && !m" :lines="6" />
    <template v-if="m">
      <PageHeader :title="m.employee_name" :subtitle="`${m.designation || ''} · ${m.department || ''}`" back="/team" />
      <div class="cols">
        <section class="panel stack">
          <div class="row"><Avatar :name="m.employee_name" :image="m.image" :size="56" />
            <dl class="kv grow"><div><dt>Joined</dt><dd>{{ fmtDate(m.date_of_joining) }}</dd></div><div><dt>Work email</dt><dd>{{ m.company_email || "—" }}</dd></div><div><dt>Phone</dt><dd>{{ m.cell_number || "—" }}</dd></div></dl></div>
          <h2>{{ t("Leave balance") }}</h2>
          <Meter v-for="b in m.balances" :key="b.leave_type" :label="b.leave_type" :value="b.remaining" :max="b.allocated" :detail="`${b.remaining} / ${b.allocated}`" />
          <h2 v-if="m.goals?.length">Goals</h2>
          <Meter v-for="g in m.goals || []" :key="g.name" :label="g.goal_name" :value="g.progress || 0" :max="100" :detail="`${g.progress || 0}%`" />
        </section>
        <aside class="panel">
          <header><h2>This month</h2></header>
          <ul class="list"><li v-for="a in m.attendance" :key="a.status"><span class="grow">{{ t(a.status) }}</span><StatusBadge :status="a.status" :label="String(a.n)" /></li></ul>
          <p class="small muted">Pay, bank and personal details aren't shown in the manager workspace.</p>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>.kv { margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; } dt { font-size: var(--fs-xs); color: var(--ink-3); } dd { margin: 0; overflow-wrap: anywhere; }</style>
