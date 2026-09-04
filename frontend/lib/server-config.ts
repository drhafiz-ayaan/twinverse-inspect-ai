import "server-only";

/**
 * The API address as seen *from the dashboard server*, which is not the address
 * the browser uses.
 *
 * `NEXT_PUBLIC_API_URL` is baked in at build time and is correct for a browser:
 * under Compose that is `http://localhost:8000/api/v1`, published from the host.
 * Inside the frontend container `localhost` is the container itself, so every
 * server-side fetch to that address is refused — and since all data fetching
 * and every proxy route in this app runs server-side, the containerised
 * dashboard could not even sign in. `POST /api/session` returned 502 while the
 * page itself returned 200, which is why it looked healthy.
 *
 * Set `API_INTERNAL_URL` to the service address on the Docker network
 * (`http://api:8000/api/v1`). Running outside containers the two are the same,
 * so it falls back to the public value and nothing changes.
 */
export const API_INTERNAL_BASE =
  process.env.API_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";
