import { cookies } from 'next/headers'
import React from 'react'
import { Locale } from '../../../../../i18n.config'
import getTrans from '@/lib/translation'
import ModifyDocuments from '@/components/_components/driver/ModifyDocuments'
import { redirect } from 'next/navigation'

export default async function UploadDocumentsPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale=(await params).locale
  const auth = await getTrans(locale,"auth")
  const token=(await cookies()).get("userToken")?.value

  // Check if driver is logged in
  const cookieStore = await cookies();
  const accountType = cookieStore.get("account_type")?.value;

  // Redirect to auth if not logged in or not a driver
  if (!token || accountType !== "normal_driver") {
    redirect(`/${locale}/auth`);
  }
  
  return (
    <div className="w-full bg-black bg-gradient py-10">
      <div className="w-full py-5">
        <div className="flex-1 w-full flex justify-center bg-gray-900/80 backdrop-blur-sm px-6 md:px-12 lg:px-20 py-10 rounded-3xl max-w-[1200px] mx-auto border border-gray-700">
          <div className="w-full" dir={locale === "en" ? "ltr" : "rtl"}>
            <ModifyDocuments locale={locale} trans={auth.CreateCaptainAccount} transInfo={auth.signup}/>
          </div>
        </div>
      </div>
    </div>
  )
}

