import { onMounted, ref, shallowRef, watch, type Ref, type WatchSource } from "vue";
import { ApiError } from "@/services/api";

/**
 * Server-state loader with an in-memory cache (never persisted - sensitive HR data stays out of storage).
 */
const cache = new Map<string, { at: number; data: any }>();

export function invalidate(prefix: string) {
  for (const k of cache.keys()) if (k.startsWith(prefix)) cache.delete(k);
}

export function useResource<T>(key: () => string, fetcher: () => Promise<T>,
  opts: { staleMs?: number; immediate?: boolean; watch?: WatchSource[] } = {}) {
  const data = shallowRef<T | null>(null) as Ref<T | null>;
  const error = ref<ApiError | null>(null);
  const loading = ref(false);
  const stale = opts.staleMs ?? 30_000;

  async function load(force = false) {
    const k = key();
    const hit = cache.get(k);
    if (hit) {
      data.value = hit.data;
      if (!force && Date.now() - hit.at < stale) return;
    }
    loading.value = !hit;
    error.value = null;
    try {
      const res = await fetcher();
      data.value = res;
      cache.set(k, { at: Date.now(), data: res });
    } catch (e: any) {
      error.value = e instanceof ApiError ? e : new ApiError(e?.message || "Something went wrong");
    } finally {
      loading.value = false;
    }
  }

  if (opts.immediate !== false) onMounted(() => load());
  if (opts.watch) watch(opts.watch, () => load());
  return { data, error, loading, reload: () => load(true), load };
}

export function useMutation<A extends any[], R>(fn: (...args: A) => Promise<R>) {
  const busy = ref(false);
  const error = ref<string | null>(null);
  async function run(...args: A): Promise<R | undefined> {
    busy.value = true;
    error.value = null;
    try {
      return await fn(...args);
    } catch (e: any) {
      error.value = e?.message || "Something went wrong";
      throw e;
    } finally {
      busy.value = false;
    }
  }
  return { busy, error, run };
}
