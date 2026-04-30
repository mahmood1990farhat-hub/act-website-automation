import Profile from "@/components/_components/auth/Profile";
import getTrans from "@/lib/translation";
import React from "react";
import { Locale } from "../../../../../i18n.config";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export default async function ProfilePage({ params }: { params: Promise<{ locale: Locale }> }) {
  const locale = (await params).locale;
  const token = (await cookies()).get("userToken")?.value;
  const accountType = (await cookies()).get("account_type")?.value;

  if (!token) {
    redirect(`/${locale}/auth`);
  }

  const authTrans = await getTrans(locale, "auth");
  const profileTrans = authTrans.Profile || {};

  return (
    <div className="min-h-screen bg-gradient py-8 md:py-12">
      <div className="container mx-auto px-4 md:px-6 lg:px-8 max-w-7xl">
        <Profile
          locale={locale}
          trans={profileTrans}
          accountType={accountType || "passenger"}
        />
      </div>
    </div>
  );
}

