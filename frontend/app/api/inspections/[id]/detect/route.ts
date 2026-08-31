import { forward } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return forward(`/inspections/${id}/detect`, { method: "POST" });
}
