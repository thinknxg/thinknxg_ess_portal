<script setup lang="ts">
import { computed } from "vue";
import { initials } from "@/utils/format";
const props = defineProps<{ name?: string | null; image?: string | null; size?: number }>();
const hue = computed(() => [...(props.name || "x")].reduce((a, c) => a + c.charCodeAt(0), 0) % 360);
</script>

<template>
  <span class="av" :style="{ width: `${size || 36}px`, height: `${size || 36}px`, fontSize: `${(size || 36) * 0.38}px`, '--h': hue }">
    <img v-if="image" :src="image" alt="" loading="lazy" />
    <span v-else aria-hidden="true">{{ initials(name) }}</span>
  </span>
</template>

<style scoped>
.av { flex: none; border-radius: 50%; overflow: hidden; display: inline-grid; place-items: center; font-weight: 600;
  background: hsl(var(--h) 30% 88%); color: hsl(var(--h) 40% 25%); }
:root[data-theme="dark"] .av { background: hsl(var(--h) 22% 24%); color: hsl(var(--h) 40% 85%); }
.av img { width: 100%; height: 100%; object-fit: cover; }
</style>
