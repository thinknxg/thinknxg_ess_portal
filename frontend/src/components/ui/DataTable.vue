<script setup lang="ts" generic="T extends Record<string, any>">
import EmptyState from "./EmptyState.vue";
defineProps<{ rows: T[]; columns: { key: string; label: string; numeric?: boolean; width?: string }[]; empty?: string; rowKey?: string; clickable?: boolean }>();
defineEmits<{ row: [row: T] }>();
</script>

<template>
  <div class="table-wrap">
    <table class="data" v-if="rows.length">
      <thead><tr><th v-for="c in columns" :key="c.key" :class="{ n: c.numeric }" :style="{ width: c.width }" scope="col">{{ c.label }}</th></tr></thead>
      <tbody>
        <tr v-for="(r, i) in rows" :key="rowKey ? r[rowKey] : i" :class="{ click: clickable }" @click="clickable && $emit('row', r)"
            :tabindex="clickable ? 0 : undefined" @keydown.enter="clickable && $emit('row', r)">
          <td v-for="c in columns" :key="c.key" :class="{ n: c.numeric }">
            <slot :name="c.key" :row="r">{{ r[c.key] ?? "—" }}</slot>
          </td>
        </tr>
      </tbody>
    </table>
    <EmptyState v-else :title="empty || 'Nothing here yet'" />
  </div>
</template>

<style scoped>
tr.click { cursor: pointer; }
tr.click:hover td { background: var(--surface-2); }
</style>
