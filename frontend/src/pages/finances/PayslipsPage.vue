<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useResource } from "@/composables/useResource";
import { Payroll } from "@/services/endpoints";
import { downloadUrl } from "@/services/api";
import { fmtDate, fmtMoney, t } from "@/i18n";
import PageHeader from "@/components/ui/PageHeader.vue";
import DataTable from "@/components/ui/DataTable.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";

const router = useRouter();
const year = ref<number | undefined>(undefined);
const masked = ref(true);
const { data, loading, error, reload } = useResource<any>(() => `payslips:${year.value}`, () => Payroll.list(year.value), { watch: [year] });
const cols = [
  { key: "period", label: "Period" }, { key: "payment_days", label: "Paid days", numeric: true },
  { key: "gross_pay", label: t("Gross pay"), numeric: true }, { key: "total_deduction", label: t("Deductions"), numeric: true },
  { key: "net_pay", label: t("Net pay"), numeric: true }, { key: "dl", label: "" },
];
const money = (v: number, c: string) => (masked.value ? "•••••" : fmtMoney(v, c));
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Payslips')" subtitle="Only you can see your payslips. Downloads are recorded for your security.">
      <select class="select" v-model="year" aria-label="Year" style="width: auto">
        <option :value="undefined">All years</option><option v-for="y in data?.years || []" :key="y" :value="y">{{ y }}</option></select>
      <button class="btn" @click="masked = !masked" :aria-pressed="!masked">{{ masked ? "Show amounts" : "Hide amounts" }}</button>
      <RouterLink to="/finances/expenses" class="btn ghost">{{ t("Expenses") }}</RouterLink>
    </PageHeader>
    <ErrorState :error="error" @retry="reload" />
    <section class="panel">
      <SkeletonLoader v-if="loading && !data" :lines="6" />
      <DataTable v-else :rows="data?.payslips || []" :columns="cols" row-key="name" clickable empty="No payslips yet" @row="(r: any) => router.push(`/finances/payslips/${r.name}`)">
        <template #period="{ row }"><strong>{{ fmtDate(row.start_date, { month: "long", year: "numeric" }) }}</strong><br><span class="small muted">{{ fmtDate(row.start_date) }} – {{ fmtDate(row.end_date) }}</span></template>
        <template #gross_pay="{ row }">{{ money(row.gross_pay, row.currency) }}</template>
        <template #total_deduction="{ row }">{{ money(row.total_deduction, row.currency) }}</template>
        <template #net_pay="{ row }"><strong>{{ money(row.net_pay, row.currency) }}</strong></template>
        <template #dl="{ row }"><a class="btn ghost sm" :href="downloadUrl('payroll.download_payslip', { name: row.name })" @click.stop>{{ t("Download") }}</a></template>
      </DataTable>
    </section>
  </div>
</template>
