import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import CancellationReviewDashboard from "@/components/_components/dashboard/CancellationReviewDashboard";
import { privatePageSeo } from "@/lib/seo";

export const dynamic = "force-dynamic";
export const metadata = privatePageSeo;

export default async function CancellationReviewPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const token = (await cookies()).get("userToken")?.value;
  if (!token) redirect(`/${locale}/admin/login`);
  // Existing dashboard layout/login are reused; the backend enforces the specific permission.
  return <CancellationReviewDashboard token={token} />;
}
