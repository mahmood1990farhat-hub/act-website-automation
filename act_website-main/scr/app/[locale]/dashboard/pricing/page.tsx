import { cookies } from 'next/headers'
import React from 'react'
import { Locale } from '../../../../../i18n.config'
import getTrans from '@/lib/translation'
import PricingSettings from '@/components/_components/dashboard/PricingSettings'
import PricingTiers from '@/components/_components/dashboard/PricingTiers'
import PeakTimeRules from '@/components/_components/dashboard/PeakTimeRules'
import AirportFees from '@/components/_components/dashboard/AirportFees'
import PricingAccordion, { AccordionItem } from '@/components/_components/dashboard/PricingAccordion'


export default async function DashboardPricingPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale = (await params).locale
  const { dashboard } = await getTrans(locale, "dashboard") 
  const token = (await cookies()).get("userToken")?.value
  
  return (
    <div className='p-4 md:p-6 max-w-full overflow-x-hidden'>
      <PricingAccordion>
        <AccordionItem title={dashboard.pricing?.title || "Pricing Settings"} defaultOpen={true}>
          <PricingSettings locale={locale} token={token} trans={dashboard} />
        </AccordionItem>
        <AccordionItem title={dashboard.tiers?.title || "Pricing Tiers Management"}>
          <PricingTiers locale={locale} token={token} trans={dashboard} />
        </AccordionItem>
        <AccordionItem title={dashboard.peakTime?.title || "Peak Time Rules"}>
          <PeakTimeRules locale={locale} token={token} trans={dashboard} />
        </AccordionItem>
        <AccordionItem title={dashboard.airportFees?.title || "Airport Fees Management"}>
          <AirportFees locale={locale} token={token} trans={dashboard} />
        </AccordionItem>
      </PricingAccordion>
    </div>
  )
}
