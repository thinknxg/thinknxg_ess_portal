<script setup lang="ts">
import { computed } from "vue";
import { useResource } from "@/composables/useResource";
import { Analytics } from "@/services/endpoints";
import { t } from "@/i18n";
import PageHeader from "@/components/ui/PageHeader.vue";
import BarChart from "@/components/hr/BarChart.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";

const { data, loading } = useResource<any>(() => "an:emp", () => Analytics.employee());
const labels = computed(() => (data.value?.attendance || []).map((r: any) => r.month.slice(5)));
const series = computed(() => [
  { name: t("Present"), values: data.value?.attendance.map((r: any) => r.Present + r["Work From Home"]) || [], color: "var(--brand)" },
  { name: t("On leave"), values: data.value?.attendance.map((r: any) => r["On Leave"] + r["Half Day"]) || [], color: "var(--info)" },
  { name: t("Absent"), values: data.value?.attendance.map((r: any) => r.Absent) || [], color: "var(--pom)" },
]);
</script>

<template>
  <div class="page">
    <PageHeader title="My insights" subtitle="Your own patterns over the last six months. Only you see this." />
    <SkeletonLoader v-if="loading && !data" :lines="6" />
    <div class="cols" v-else-if="data">
      <section class="panel"><header><h2>Attendance by month</h2></header><BarChart title="Attendance by month" :labels="labels" :series="series" stacked /></section>
      <section class="panel"><header><h2>Leave taken this year</h2></header>
        <ul class="list"><li v-for="l in data.leave_usage" :key="l.leave_type"><span class="grow">{{ l.leave_type }}</span><span class="num">{{ l.days }}</span></li></ul>
        <p class="small muted" v-if="data.avg_leave_turnaround_hours">Your leave requests were decided in {{ data.avg_leave_turnaround_hours }} hours on average.</p></section>
    </div>
  </div>
</template>
