import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { Locale } from "../../../../../i18n.config";
import { privatePageSeo } from "@/lib/seo";
import DriverVehicleSupplement from "@/components/_components/auth/captain/DriverVehicleSupplement";

export const metadata = privatePageSeo;

export default async function DriverApplicationStatusPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  const session = await cookies();
  const token = session.get("userToken")?.value;
  const account = session.get("account_type")?.value;
  if (!token || account !== "normal_driver") redirect(`/${locale}/auth`);

  let application: any = null;
  try {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL || "";
    const response = await fetch(base + "/api/drivers/onboarding/status/", {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (response.ok) application = await response.json();
  } catch { /* Display safe status unavailable message, never token. */ }

  return (
    <main className="mx-auto my-12 max-w-xl rounded-xl border border-gray-700 bg-gray-900 p-6 text-white">
      <h1 className="text-2xl font-bold text-yellow-400">ACT Driver Application</h1>
      {application ? (
        <>
          <p className="mt-4">Application #{application.request?.id} — <strong>{String(application.status).replace(/_/g, " ")}</strong></p>
          {application.request?.submission_mode === "unified" ? (
            <>
              <p className="mt-3">ACT is verifying your application and documents. No additional standard document stage is required.</p>
              {application.request?.awaiting_vehicle && (
                <>
                  <p className="mt-3 rounded-lg border border-yellow-400 p-3 text-yellow-100">
                    You can apply without a vehicle, but cannot receive trips until ACT verifies a licensed vehicle and its documents.
                  </p>
                  {application.status === "pending" && <DriverVehicleSupplement token={token} />}
                </>
              )}
            </>
          ) : <p className="mt-3">{application.next_step}</p>}
          {application.status === "final_approved" && (
            <p className="mt-4 text-green-300">Your driver verification is complete. Re-sign in for updated access.</p>
          )}
        </>
      ) : (
        <p className="mt-4">Application status is temporarily unavailable. Please try again later or contact ACT support.</p>
      )}
      <p className="mt-6 text-sm">
        For application questions, email{" "}
        <a className="text-yellow-400 underline" href="mailto:info@airportandcitytransfer.com">
          info@airportandcitytransfer.com
        </a>.
      </p>
      <Link className="mt-5 inline-block text-yellow-400 underline" href={`/${locale}`}>Return to homepage</Link>
    </main>
  );
}
