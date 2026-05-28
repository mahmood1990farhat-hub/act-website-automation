import Asidebar from "@/components/_components/driver/Asidebar";
import React from "react";
import { Locale } from "../../../../i18n.config";
import getTrans from "@/lib/translation";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import Header from "@/components/_components/header/Header";
import Footer from "@/components/_components/footer/Footer";

export default async function LayoutDriver({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const localeTyped = locale as Locale;
  const { aside, adminVerification, sidebar } = await getTrans(localeTyped, "driver");
  const { navbar, footer, policy_and_terms, faqs } = await getTrans(localeTyped, 'home');

  // Check authentication
  const cookieStore = await cookies();
  const accountType = cookieStore.get("account_type")?.value;
  const isAdminVerified = cookieStore.get("is_admin_verified")?.value === "true";
  const token = cookieStore.get("userToken")?.value;

  // Get current pathname from headers (set by middleware)
  const headersList = await headers();
  const pathname = headersList.get("x-pathname") || headersList.get("x-url") || "";
  const isUploadDocuments = pathname.includes("upload-documents");

  // Redirect if not authenticated
  if (!token) {
    redirect(`/${localeTyped}/auth`);
  }

  // Redirect if not a driver
  if (accountType !== "normal_driver") {
    redirect(`/${localeTyped}`);
  }

  // Allow upload-documents page even if not verified (for needs_modification status)
  // For other driver routes, require verification
  if (!isAdminVerified && !isUploadDocuments) {
    redirect(`/${localeTyped}`);
  }

  // For upload-documents page, use site layout with Header and Footer (like CreateCaptainAccount)
  if (isUploadDocuments) {
    return (
      <>
        <main className="relative overflow-clip bg-cover bg-center text-white min-h-[700px]">
          <Header navbar={navbar} locale={localeTyped} token={token} />
          {children}
        </main>
        <Footer footer={footer} privacyPolicy={policy_and_terms.policy} terms={policy_and_terms.terms} faqs={faqs} />
      </>
    );
  }

  // For verified drivers, show full layout with sidebar
  return (
    <div className="flex">
      <Asidebar trans={aside} adminVerification={adminVerification} sidebar={sidebar} />

      {/* Content Area */}
      <main className="flex-1 max-md:pt-15 max-md:px-2 p-5  h-screen overflow-y-auto bg-gray-100 on-scrollbar">
        {children}
      </main>
    </div>
  );
}
