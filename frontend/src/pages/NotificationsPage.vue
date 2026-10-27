<script setup lang="ts">
import { useResource, invalidate } from "@/composables/useResource";
import { Notifications } from "@/services/endpoints";
import { useSession } from "@/stores/session";
import { relative, t } from "@/i18n";
import PageHeader from "@/components/ui/PageHeader.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";

const s = useSession();
const { data, loading, reload } = useResource<any[]>(() => "notifications", () => Notifications.list(), { staleMs: 5_000 });
async function readAll() { const r = await Notifications.markRead(undefined, 1); s.unread = r.unread; invalidate("notifications"); reload(); }
async function readOne(n: any) { if (!n.read) { const r = await Notifications.markRead([n.name]); n.read = 1; s.unread = r.unread; } }
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Notifications')">
      <button class="btn" @click="readAll" :disabled="!s.unread">Mark all as read</button>
      <RouterLink to="/settings" class="btn ghost">{{ t("Settings") }}</RouterLink>
    </PageHeader>
    <SkeletonLoader v-if="loading && !data" />
    <section class="panel" v-else>
      <ul class="list" v-if="data?.length">
        <li v-for="n in data" :key="n.name" :class="{ unread: !n.read }" @click="readOne(n)">
          <span class="grow"><span class="title">{{ n.subject }}</span><br><span class="muted small">{{ n.email_content }}</span></span>
          <span class="muted small">{{ relative(n.creation) }}</span>
        </li>
      </ul>
      <EmptyState v-else title="No notifications yet" icon="bell" />
    </section>
  </div>
</template>

<style scoped>
.list li { cursor: default; }
.unread .title::before { content: ""; display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--brand); margin-inline-end: 8px; vertical-align: 2px; }
</style>
