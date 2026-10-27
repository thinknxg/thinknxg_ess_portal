<script setup lang="ts">
import { ref } from "vue";
import { useRoute } from "vue-router";
import { useResource, invalidate } from "@/composables/useResource";
import { Goals } from "@/services/endpoints";
import { fmtDate, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import SegmentTabs from "@/components/ui/SegmentTabs.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import Meter from "@/components/hr/Meter.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";

const route = useRoute();
const ui = useUi();
const tab = ref((route.query.tab as string) || "goals");
const { data, loading, reload } = useResource<any>(() => "goals", () => Goals.overview());
const editing = ref<string | null>(null);
const val = ref(0);
async function save(name: string) {
  try { await Goals.progress(name, val.value); ui.toast("Progress updated"); editing.value = null; invalidate("goals"); reload(); }
  catch (e: any) { ui.toast(e.message, "error"); }
}
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Goals & learning')" />
    <SegmentTabs v-model="tab" :tabs="[{ value: 'goals', label: 'Goals', count: data?.goals?.length }, { value: 'reviews', label: 'Reviews' }, { value: 'learning', label: 'Learning', count: data?.training?.length }]" />
    <SkeletonLoader v-if="loading && !data" :lines="6" />
    <section v-else-if="tab === 'goals'" class="panel">
      <div v-if="data?.onboarding" class="onb">
        <Meter label="Onboarding" :value="data.onboarding.progress" :max="100" :detail="`${data.onboarding.progress}%`" />
        <ul class="list small"><li v-for="a in data.onboarding.activities" :key="a.activity_name"><span class="grow">{{ a.activity_name }}</span><StatusBadge :status="a.completed ? 'Completed' : 'Pending'" /></li></ul>
      </div>
      <ul class="list" v-if="data?.goals?.length">
        <li v-for="g in data.goals.filter((x: any) => !x.is_group)" :key="g.name" class="goal">
          <div class="grow stack" style="gap: 8px">
            <div class="spread"><span class="title">{{ g.goal_name }}</span><span class="small muted">{{ g.appraisal_cycle }} · due {{ fmtDate(g.end_date) }}</span></div>
            <Meter :label="g.kra || 'Progress'" :value="g.progress || 0" :max="100" :detail="`${g.progress || 0}%`" />
            <div v-if="editing === g.name" class="row">
              <label :for="`gp-${g.name}`" class="sr-only">Progress</label>
              <input :id="`gp-${g.name}`" type="range" min="0" max="100" step="5" v-model.number="val" class="grow" />
              <span class="num">{{ val }}%</span><button class="btn sm primary" @click="save(g.name)">{{ t("Save") }}</button><button class="btn sm ghost" @click="editing = null">{{ t("Cancel") }}</button>
            </div>
            <div v-else><button class="btn sm" @click="editing = g.name; val = g.progress || 0">Update progress</button></div>
          </div>
        </li>
      </ul>
      <EmptyState v-else title="No goals set yet" text="Goals appear here once your manager sets them for the current appraisal cycle." icon="target" />
    </section>
    <section v-else-if="tab === 'reviews'" class="panel">
      <ul class="list" v-if="data?.appraisals?.length">
        <li v-for="a in data.appraisals" :key="a.name"><span class="grow"><span class="title">{{ a.appraisal_cycle }}</span></span>
          <span class="num" v-if="a.final_score">Score {{ a.final_score }}</span><StatusBadge :status="a.status || (a.docstatus === 1 ? 'Completed' : 'Draft')" /></li>
      </ul>
      <EmptyState v-else title="No reviews yet" icon="target" />
      <p class="small muted" v-if="data?.feedback_count">You've received {{ data.feedback_count }} feedback entries.</p>
    </section>
    <section v-else class="panel">
      <ul class="list" v-if="data?.training?.length">
        <li v-for="tr in data.training" :key="tr.name"><span class="grow"><span class="title">{{ tr.event_name }}</span><br><span class="small muted">{{ fmtDate(tr.start_time) }}<template v-if="tr.location"> · {{ tr.location }}</template></span></span>
          <StatusBadge :status="tr.attendee_status || tr.event_status" /></li>
      </ul>
      <EmptyState v-else title="No training scheduled" icon="target" />
    </section>
  </div>
</template>

<style scoped>.onb { padding-bottom: 16px; margin-bottom: 8px; border-bottom: 1px solid var(--line); } .goal { align-items: flex-start; }</style>
