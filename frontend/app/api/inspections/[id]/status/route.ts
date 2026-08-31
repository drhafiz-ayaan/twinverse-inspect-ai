import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

/**
 * Polled by the upload panel while detection runs.
 *
 * Detection is fire-and-forget on the API side — POST /detect returns as soon
 * as the work is queued — so the only way to know it finished is to watch the
 * inspection's status move pending → processing → completed.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return forward(`/inspections/${id}`, { method: "GET" });
}
