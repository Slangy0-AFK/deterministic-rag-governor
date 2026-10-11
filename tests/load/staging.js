import http from "k6/http";
import { check, fail } from "k6";

const rawBaseUrl = __ENV.STAGING_BASE_URL || "";
const parsedBaseUrl = rawBaseUrl.match(/^https?:\/\/([^/?#]+)(?:\/[^?#]*)?$/i);

if (
  !parsedBaseUrl ||
  parsedBaseUrl[1].includes("@") ||
  !/(^|[.-])staging([.-]|$)/i.test(parsedBaseUrl[1].replace(/:\d+$/, ""))
) {
  fail("STAGING_BASE_URL must be an HTTP(S) staging URL; refusing to load test another environment");
}

const BASE_URL = rawBaseUrl.replace(/\/+$/, "");

export const options = {
  vus: 5,
  duration: "1m",
  thresholds: {
    checks: ["rate>0.99"],
    http_req_duration: ["p(95)<1000"],
  },
};

export default function () {
  for (const path of ["/healthz", "/readyz"]) {
    const response = http.get(`${BASE_URL}${path}`);
    check(response, {
      [`${path} responds successfully`]: (result) => result.status === 200,
    });
  }
}
