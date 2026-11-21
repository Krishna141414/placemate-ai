import { expect, test as setup } from "@playwright/test";

import { API, STATE } from "./helpers";

// Log in once per demo account and save the session cookie, so the tests stay
// well under the login rate limit (10 a minute).
for (const role of ["student", "coordinator"] as const) {
  setup(`log in as the demo ${role}`, async ({ request }) => {
    const credentials =
      role === "student"
        ? { email: "student@placemate.demo", password: "Student@123" }
        : { email: "coordinator@placemate.demo", password: "Coord@123" };
    const response = await request.post(`${API}/api/auth/login`, {
      data: credentials,
      headers: { Origin: "http://localhost:3000" },
    });
    expect(response.status()).toBe(200);
    await request.storageState({ path: STATE[role] });
  });
}
