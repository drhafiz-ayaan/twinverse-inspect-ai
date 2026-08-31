import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const body = await request.text();
  return forward("/assets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
}
