'use server'

import Auth from "@/components/_components/auth/Auth";
import getTrans from "@/lib/translation";
import { Locale } from "../../../../i18n.config";

type typePrpos = {
  locale: Locale 

};

export default async function AuthwithTrans({ locale }: typePrpos) {





  const auth = await getTrans(locale, "auth");

  return (
    <div>
      <Auth locale={locale} trans={auth}  />
    </div>
  );
}
