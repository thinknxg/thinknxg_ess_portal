<script setup lang="ts">
import { useRoute } from "vue-router";
import { useResource } from "@/composables/useResource";
import { Payroll } from "@/services/endpoints";
import { downloadUrl } from "@/services/api";
import { fmtDate, fmtMoney, t } from "@/i18n";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";

const route = useRoute();
const name = String(route.params.name);
const { data: p, loading, error, reload } = useResource<any>(() => `payslip:${name}`, () => Payroll.detail(name));
</script>

<template>
  <div class="page">
    <PageHeader :title="p ? fmtDate(p.start_date, { month: 'long', year: 'numeric' }) : t('Payslips')" :subtitle="p ? `${fmtDate(p.start_date)} – ${fmtDate(p.end_date)}` : ''" back="/finances/payslips">
      <a class="btn primary" :href="downloadUrl('payroll.download_payslip', { name })">{{ t("Download") }} PDF</a>
    </PageHeader>
    <ErrorState :error="error" @retry="reload" />
    <SkeletonLoader v-if="loading && !p" :lines="8" />
    <template v-if="p">
      <section class="net">
        <div><span class="muted">{{ t("Net pay") }}</span><p class="v num">{{ fmtMoney(p.net_pay, p.currency) }}</p></div>
        <div><span class="muted">{{ t("Gross pay") }}</span><p class="v2 num">{{ fmtMoney(p.gross_pay, p.currency) }}</p></div>
        <div><span class="muted">{{ t("Deductions") }}</span><p class="v2 num">{{ fmtMoney(p.total_deduction, p.currency) }}</p></div>
        <div><span class="muted">Paid days</span><p class="v2 num">{{ p.payment_days }}<span class="muted small"> / {{ p.total_working_days }}</span></p></div>
      </section>
      <div class="cols-2">
        <section class="panel"><header><h2>{{ t("Earnings") }}</h2></header>
          <table class="data"><tbody><tr v-for="e in p.earnings" :key="e.component"><td>{{ e.component }}</td><td class="n">{{ fmtMoney(e.amount, p.currency) }}</td></tr>
            <tr class="tot"><td>{{ t("Total") }}</td><td class="n">{{ fmtMoney(p.gross_pay, p.currency) }}</td></tr></tbody></table></section>
        <section class="panel"><header><h2>{{ t("Deductions") }}</h2></header>
          <table class="data"><tbody><tr v-for="e in p.deductions" :key="e.component"><td>{{ e.component }}</td><td class="n">{{ fmtMoney(e.amount, p.currency) }}</td></tr>
            <tr v-if="!p.deductions.length"><td class="muted">No deductions this period</td><td /></tr>
            <tr class="tot"><td>{{ t("Total") }}</td><td class="n">{{ fmtMoney(p.total_deduction, p.currency) }}</td></tr></tbody></table></section>
      </div>
      <section class="panel"><header><h2>{{ t("Year to date") }}</h2></header>
        <div class="ytd"><div><span class="muted small">{{ t("Gross pay") }}</span><p class="num">{{ fmtMoney(p.ytd.gross, p.currency) }}</p></div>
          <div><span class="muted small">{{ t("Deductions") }}</span><p class="num">{{ fmtMoney(p.ytd.deductions, p.currency) }}</p></div>
          <div><span class="muted small">{{ t("Net pay") }}</span><p class="num">{{ fmtMoney(p.ytd.net, p.currency) }}</p></div></div>
        <p class="small muted" style="margin-top: 12px">Something looks wrong? <RouterLink :to="{ path: '/support/new', query: { category: 'Payroll & Salary', subject: `Query on payslip ${name}` } }">Raise a payroll query</RouterLink>.</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.net { display: grid; grid-template-columns: 1.4fr repeat(3, 1fr); gap: 20px; padding: 24px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg); border-top: 4px solid var(--brand); }
.v { font-size: var(--fs-2xl); font-weight: 600; letter-spacing: -0.03em; }
.v2 { font-size: var(--fs-lg); font-weight: 500; }
.tot td { font-weight: 600; border-top: 2px solid var(--line-strong); }
.ytd { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; } .ytd p { font-weight: 600; font-size: var(--fs-lg); }
@media (max-width: 760px) { .net { grid-template-columns: 1fr 1fr; } }
</style>
