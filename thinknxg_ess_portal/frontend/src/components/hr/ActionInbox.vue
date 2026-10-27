<script setup lang="ts">
import type { InboxItem } from "@/types";
import { fmtDate, t } from "@/i18n";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import EssIcon from "@/components/ui/EssIcon.vue";

defineProps<{ items: InboxItem[]; compact?: boolean }>();
const ICON: Record<string, string> = { leave: "sun", expense: "receipt", ticket: "lifebuoy", rate: "star", doc: "file",
  policy: "shield", edoc: "file", todo: "check", training: "target", approve: "check" };
const icon = (id: string) => ICON[id.split(":")[0]] || "inbox";
</script>

<template>
  <ul class="list" v-if="items.length">
    <li v-for="i in items" :key="i.id" :class="['p-' + i.priority]">
      <RouterLink :to="i.route" class="rowlink">
        <span class="ic"><EssIcon :name="icon(i.id)" :size="18" /></span>
        <span class="grow">
          <span class="title">{{ i.title }}</span>
          <span v-if="i.due_date" class="muted small"> · {{ fmtDate(i.due_date) }}</span>
        </span>
        <StatusBadge v-if="!compact" :status="i.status" :tone="i.priority === 'high' ? 'warn' : undefined" :label="i.status === 'action' ? 'Action needed' : undefined" />
        <EssIcon name="chevron" :size="16" />
      </RouterLink>
    </li>
  </ul>
  <EmptyState v-else :title="t('Nothing waiting for you')" :text="t('You\'re all caught up.')" icon="check" />
</template>

<style scoped>
.ic { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; background: var(--surface-2); color: var(--ink-2); flex: none; }
.p-high .ic { background: var(--saffron-soft); color: var(--saffron-ink); }
.title { display: inline; }
</style>
