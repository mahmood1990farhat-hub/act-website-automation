import assert from "node:assert/strict";
import test from "node:test";
import { buildTripTrackingUrl } from "../../src/lib/trip-tracking-url.ts";

test("HTTPS tracking uses the configured REST origin and the existing root route", () => {
  for (const base of [
    "https://journey-api.example.invalid",
    "https://journey-api.example.invalid/",
    "https://journey-api.example.invalid/api",
    "https://journey-api.example.invalid/api/v1/",
  ]) {
    assert.equal(buildTripTrackingUrl(base, "101"),
      "wss://journey-api.example.invalid/ws/trips/101/tracking/");
  }
});

test("HTTP loopback supports the existing isolated runner and preserves its port", () => {
  assert.equal(buildTripTrackingUrl("http://127.0.0.1:8000/api", 101),
    "ws://127.0.0.1:8000/ws/trips/101/tracking/");
  assert.equal(buildTripTrackingUrl("http://localhost:8001", "202"),
    "ws://localhost:8001/ws/trips/202/tracking/");
});

test("IPv6 and non-default HTTPS ports retain their configured authority", () => {
  assert.equal(buildTripTrackingUrl("http://[::1]:8000/api", "101"),
    "ws://[::1]:8000/ws/trips/101/tracking/");
  assert.equal(buildTripTrackingUrl("https://journey-api.example.invalid:8443/api", "101"),
    "wss://journey-api.example.invalid:8443/ws/trips/101/tracking/");
});

test("missing or blank configuration has no default backend", () => {
  for (const base of [undefined, null, "", " ", "\n", false, 123]) {
    assert.equal(buildTripTrackingUrl(base, "101"), null);
  }
});

test("relative and non-HTTP API bases cannot select an unintended socket", () => {
  for (const base of ["/api", "//journey-api.example.invalid", "journey-api.example.invalid",
    "ftp://journey-api.example.invalid", "ws://journey-api.example.invalid",
    "wss://journey-api.example.invalid", "file:///api", "javascript:alert(1)"]) {
    assert.equal(buildTripTrackingUrl(base, "101"), null, base);
  }
});

test("malformed schemes and authorities are rejected instead of URL-normalized", () => {
  for (const base of ["https:/journey-api.example.invalid", "https:journey-api.example.invalid",
    "https:///journey-api.example.invalid", "https:////journey-api.example.invalid",
    "https://", "http://[::1", "https://journey-api.example.invalid:invalid",
    "https:\\journey-api.example.invalid", "https://journey-api.example.invalid\\api"]) {
    assert.equal(buildTripTrackingUrl(base, "101"), null, base);
  }
});

test("credentials cannot be carried from an API base into the WebSocket URL", () => {
  for (const base of ["https://user@journey-api.example.invalid",
    "https://user:password@journey-api.example.invalid/api",
    "https://:password@journey-api.example.invalid"]) {
    assert.equal(buildTripTrackingUrl(base, "101"), null);
  }
});

test("query and fragment configuration is rejected, including empty delimiters", () => {
  for (const suffix of ["?token=synthetic", "#fragment", "?", "#", "/api?x=1", "/api#x"]) {
    assert.equal(buildTripTrackingUrl(`https://journey-api.example.invalid${suffix}`, "101"), null);
  }
});

test("whitespace and control characters cannot be silently stripped from configuration", () => {
  for (const base of [" https://journey-api.example.invalid", "https://journey-api.example.invalid ",
    "https://journey-\napi.example.invalid", "https://journey-api.example.invalid/\tapi",
    "https://journey-api.example.invalid/\u0000", "https://journey-api.example.invalid/\u007f"]) {
    assert.equal(buildTripTrackingUrl(base, "101"), null);
  }
});

test("trip IDs cannot alter the backend route or attach credentials/query data", () => {
  for (const id of ["", " 101", "101 ", "../101", "101/../../other", "101?token=synthetic",
    "101#fragment", "101%2fother", "1.5", "-1", "1e2", "١٠١", "101\n", null, undefined, {}, []]) {
    assert.equal(buildTripTrackingUrl("https://journey-api.example.invalid", id), null);
  }
});

test("numeric IDs remain exact and unsafe numeric representations fail closed", () => {
  assert.equal(buildTripTrackingUrl("https://journey-api.example.invalid", "9007199254740993"),
    "wss://journey-api.example.invalid/ws/trips/9007199254740993/tracking/");
  for (const id of [-1, 1.5, Number.NaN, Number.POSITIVE_INFINITY, Number.MAX_SAFE_INTEGER + 1]) {
    assert.equal(buildTripTrackingUrl("https://journey-api.example.invalid", id), null);
  }
});

test("standard URL case normalization preserves the selected environment", () => {
  assert.equal(buildTripTrackingUrl("HTTPS://JOURNEY-API.EXAMPLE.INVALID/api", "202"),
    "wss://journey-api.example.invalid/ws/trips/202/tracking/");
});
