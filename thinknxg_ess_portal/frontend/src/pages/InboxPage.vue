<script setup lang="ts">
import { computed, ref } from "vue";
import { useResource } from "@/composables/useResource";
import { Inbox } from "@/services/endpoints";
import { queue, discard, flush } from "@/services/offlineQueue";
import { t, fmtDate } from "@/i18n";
import type { InboxItem } from "@/types";
import ActionInbox from "@/components/hr/ActionInbox.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SegmentTabs from "@/components/ui/SegmentTabs.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";

const filter = ref("all");
const extra = ref<InboxItem[]>([]);
const cursor = ref<string | null>(null);
const { data, loading, error, reload } = useResource<any>(() => "inbox", async () => {
  const r = await Inbox.items();
  extra.value = [];
  cursor.value = r.next_cursor;
  return r;
}, { staleMs: 10_000 });
const all = computed<InboxItem[]>(() => [...(data.value?.items || []), ...extra.value]);
const approvals = computed(() => all.value.filter((i) => i.type.endsWith("_approval")));
const mine = computed(() => all.value.filter((i) => !i.type.endsWith("_approval")));
const shown = computed(() => (filter.value === "approvals" ? approvals.value : filter.value === "mine" ? mine.value : all.value));
async function more() {
  if (!cursor.value) return;
  const r = await Inbox.items(cursor.value);
  extra.value.push(...r.items);
  cursor.value = r.next_cursor;
}
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Inbox')" subtitle="Everything that needs an action from you, across HR, in one list." />
    <section class="panel" v-if="queue.items.length">
      <header><h2>{{ t("Waiting to send") }}</h2><button class="btn sm" @click="flush()">Send now</button></header>
      <ul class="list">
        <li v-for="q in queue.items" :key="q.id">
          <span class="grow"><span class="title">{{ q.label }}</span><br><span class="small muted">Saved {{ fmtDate(q.created) }}{{ q.error ? ` · ${q.error}` : "" }}</span></span>
          <StatusBadge :status="q.state === 'failed' ? 'Failed' : 'Queued'" />
          <button class="btn ghost sm" @click="discard(q.id)">Discard</button>
        </li>
      </ul>
    </section>
    <SegmentTabs v-model="filter" :tabs="[{ value: 'all', label: t('All'), count: all.length }, { value: 'mine', label: 'For me', count: mine.length }, { value: 'approvals', label: t('Approvals'), count: approvals.length }]" />
    <ErrorState :error="error" @retry="reload" />
    <SkeletonLoader v-if="loading && !data" :lines="6" />
    <section class="panel" v-else-if="data">
      <ActionInbox :items="shown" />
      <button v-if="cursor" class="btn sm more" @click="more">Show more</button>
    </section>
  </div>
</template>

<style scoped>.more { margin-top: 12px; }</style>
