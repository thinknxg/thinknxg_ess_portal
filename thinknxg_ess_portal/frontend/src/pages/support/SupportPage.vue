<script setup lang="ts">
import { ref } from "vue";
import { useResource } from "@/composables/useResource";
import { Helpdesk } from "@/services/endpoints";
import { fmtDate, t } from "@/i18n";
import PageHeader from "@/components/ui/PageHeader.vue";
import SegmentTabs from "@/components/ui/SegmentTabs.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";

const status = ref("open");
const { data, loading } = useResource<any[]>(() => `tickets:${status.value}`, () => Helpdesk.mine(status.value), { watch: [status] });
const q = ref("");
const faqs = ref<any[]>([]);
async function searchFaq() { faqs.value = q.value.trim().length > 2 ? await Helpdesk.faqs(q.value) : []; }
</script>

<template>
  <div class="page">
    <PageHeader :title="t('HR helpdesk')" subtitle="Ask HR anything. You'll see who's handling it and when to expect an answer.">
      <RouterLink to="/assistant" class="btn">{{ t("HR assistant") }}</RouterLink>
      <RouterLink to="/support/new" class="btn primary">{{ t("New ticket") }}</RouterLink>
    </PageHeader>
    <section class="panel">
      <form class="row" @submit.prevent="searchFaq" role="search"><label for="faq" class="sr-only">Search answers</label>
        <input id="faq" class="input grow" v-model="q" placeholder="Search answers before raising a ticket" /><button class="btn">Search</button></form>
      <ul class="list" v-if="faqs.length" style="margin-top: 12px"><li v-for="f in faqs" :key="f.title + f.section"><span class="grow"><span class="title">{{ f.title }}</span><br><span class="small muted">{{ f.snippet }}…</span></span></li></ul>
    </section>
    <SegmentTabs v-model="status" :tabs="[{ value: 'open', label: t('Open') }, { value: 'closed', label: t('Closed') }]" />
    <section class="panel">
      <SkeletonLoader v-if="loading && !data" />
      <ul class="list" v-else-if="data?.length">
        <li v-for="tk in data" :key="tk.name"><RouterLink :to="`/support/${tk.name}`" class="rowlink">
          <span class="grow"><span class="title">{{ tk.subject }}</span><br><span class="small muted">{{ tk.name }} · {{ tk.category }} · {{ fmtDate(tk.creation) }}</span></span>
          <StatusBadge :status="tk.status" /></RouterLink></li>
      </ul>
      <EmptyState v-else :title="status === 'open' ? 'No open tickets' : 'No closed tickets'" icon="lifebuoy" :action-label="t('New ticket')" action-to="/support/new" />
    </section>
  </div>
</template>
