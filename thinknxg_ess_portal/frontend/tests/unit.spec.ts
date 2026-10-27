import { describe, expect, it, beforeEach } from "vitest";
import { renderMarkdown } from "@/utils/markdown";
import { toneFor, minutesOf, addDays } from "@/utils/format";
import { queue, enqueue, discard, canQueue } from "@/services/offlineQueue";

describe("assistant markdown renderer", () => {
  it("escapes raw HTML so model output cannot inject markup", () => {
    const html = renderMarkdown('<img src=x onerror="alert(1)"> **bold**');
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;img");
    expect(html).toContain("<strong>bold</strong>");
  });
  it("only links to portal routes or https", () => {
    expect(renderMarkdown("[ok](/ess/leave)")).toContain('href="/ess/leave"');
    expect(renderMarkdown("[bad](javascript:alert(1))")).not.toContain("href=");
    expect(renderMarkdown("[ext](https://example.com)")).toContain('rel="noopener noreferrer"');
  });
  it("renders lists and citation markers", () => {
    const html = renderMarkdown("- one [1]\n- two");
    expect(html).toContain("<ul>");
    expect(html).toContain('<sup class="cite-ref">1</sup>');
  });
});

describe("formatting helpers", () => {
  it("maps statuses to tones", () => {
    expect(toneFor("Approved")).toBe("ok");
    expect(toneFor("Breached")).toBe("bad");
    expect(toneFor("At Risk")).toBe("warn");
  });
  it("parses times and shifts dates", () => {
    expect(minutesOf("08:30:00")).toBe(510);
    expect(minutesOf("2026-10-24 17:05:00")).toBe(1025);
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
  });
});

describe("offline queue", () => {
  beforeEach(() => { queue.items.splice(0); });
  it("only queues low-risk actions", () => {
    expect(canQueue("leave.create_request")).toBe(true);
    expect(canQueue("attendance.check_in")).toBe(false);
    expect(canQueue("approvals.act")).toBe(false);
    expect(() => enqueue("attendance.check_in", {}, "x")).toThrow();
  });
  it("keeps the client request id so replays are idempotent", () => {
    const item = enqueue("helpdesk.create_ticket", { client_request_id: "abc", subject: "s" }, "Ticket");
    expect(item.params.client_request_id).toBe("abc");
    expect(queue.items).toHaveLength(1);
    discard(item.id);
    expect(queue.items).toHaveLength(0);
  });
});
