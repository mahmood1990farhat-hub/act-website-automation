import { redirect } from "next/navigation";
import { i18n } from "../../i18n.config";

// Root page - redirects to default locale
// This is a fallback in case middleware doesn't execute
export default function RootPage() {
  redirect(`/${i18n.defaultLocale}`);
}

