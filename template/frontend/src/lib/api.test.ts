import { describe, it, expect, vi, beforeEach } from "vitest";
import { submitQuery } from "./api";

describe("submitQuery", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("sends POST to /api/query/ with text payload", async () => {
    const mockResponse = { message: "echo" };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await submitQuery("hello");

    expect(fetch).toHaveBeenCalledWith("/api/query/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "hello" }),
    });
    expect(result).toEqual({ message: "echo" });
  });

  it("throws on non-ok response", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    });

    await expect(submitQuery("fail")).rejects.toThrow("Request failed: 500");
  });
});
