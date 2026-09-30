import assert from "node:assert/strict";
import test from "node:test";
import { validatePublicUrl } from "../src/artifactStore.js";

const expectReject = async (url: string, marker: string) => {
  await assert.rejects(() => validatePublicUrl(url), (error: unknown) => {
    return error instanceof Error && error.message.includes(marker);
  });
};

test("rejects non-http schemes", async () => {
  await expectReject("file:///etc/passwd", "ONLY_HTTP_HTTPS_ALLOWED");
});

test("rejects localhost", async () => {
  await expectReject("http://localhost/x", "LOCALHOST_FORBIDDEN");
  await expectReject("http://foo.localhost/x", "LOCALHOST_FORBIDDEN");
});

test("rejects loopback/private/link-local IPv4 literals", async () => {
  await expectReject("http://127.0.0.1/x", "NON_PUBLIC_ADDRESS_FORBIDDEN");
  await expectReject("http://10.1.2.3/x", "NON_PUBLIC_ADDRESS_FORBIDDEN");
  await expectReject("http://172.16.1.2/x", "NON_PUBLIC_ADDRESS_FORBIDDEN");
  await expectReject("http://192.168.1.2/x", "NON_PUBLIC_ADDRESS_FORBIDDEN");
  await expectReject("http://169.254.169.254/latest/meta-data", "NON_PUBLIC_ADDRESS_FORBIDDEN");
});

test("rejects IPv6 loopback/private literals", async () => {
  await expectReject("http://[::1]/x", "NON_PUBLIC_ADDRESS_FORBIDDEN");
  await expectReject("http://[fc00::1]/x", "NON_PUBLIC_ADDRESS_FORBIDDEN");
  await expectReject("http://[fe80::1]/x", "NON_PUBLIC_ADDRESS_FORBIDDEN");
});

test("rejects URL userinfo", async () => {
  await expectReject("https://user:pass@example.com/x", "URL_USERINFO_FORBIDDEN");
});
