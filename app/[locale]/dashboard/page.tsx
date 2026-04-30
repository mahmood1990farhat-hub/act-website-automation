import { redirect } from 'next/navigation'
import { Locale } from '../../../../i18n.config'

export default async function DashboardPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale = (await params).locale
  redirect(`/${locale}/dashboard/overview`)
}
