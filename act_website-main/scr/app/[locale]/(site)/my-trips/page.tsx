import TripsPassenger from '@/components/_components/Trips/passenger'
import getTrans from '@/lib/translation'
import React from 'react'
import { Locale } from '../../../../../i18n.config'
import { cookies } from 'next/headers'
import { FaSuitcase } from 'react-icons/fa'

export default async function MytripsPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale= (await params).locale

  const transMyTrips=await getTrans(locale,"tripsPassenger")
  const token = (await cookies()).get("userToken")?.value
  
  
  return (
    <div className='min-h-screen bg-gradient py-8 md:py-12'>
      <div className='container mx-auto px-4 md:px-6 lg:px-8 max-w-7xl'>
        {/* Page Header */}
        {/* <div className='mb-8 md:mb-12'>
          <div className='flex items-center justify-center gap-4 mb-4'>
            <div className='bg-primary/20 p-3 md:p-4 rounded-xl'>
              <FaSuitcase className='text-primary text-2xl md:text-3xl' />
            </div>
            <h1 className='text-3xl md:text-4xl lg:text-5xl font-extrabold bg-gradient-to-r from-primary via-white to-primary bg-clip-text text-transparent'>
              {transMyTrips.title}
            </h1>
          </div>
          <div className='w-24 h-1 bg-primary mx-auto rounded-full'></div>
        </div> */}

        {/* Main Content */}
        <TripsPassenger trans={transMyTrips} token={token} locale={locale}/>
      </div>
    </div>
  )
}
