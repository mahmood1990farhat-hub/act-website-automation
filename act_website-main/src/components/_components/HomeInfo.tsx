import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  MapPin,
  Calendar,
  Users,
  CheckCircle,
  ArrowRight,
} from "lucide-react";
import Image from "next/image";
import React from "react";
import ServiceImage1 from '@/../public/images/service1.webp';
import ServiceImage2 from '@/../public/images/service2.webp';
import DriverPic from '@/../public/images/driver.png';
import { Button } from "../ui/button";
import Link from "next/link";

type BookingSectionProps = {
  booking_data: {
    booking_title: {
      span: string;
      title: string;
      titlespan: string;
      subtitle: string;
    };
    sections: {
      title: string;
      text: string;
    }[];
    howToWork: {
      title: string;
      desc: string;
    }[];
    services: {
      title: string;
      subtitle: string;
    };
    joinUs: {
      title: string,
      subtitle: string,
      passenger: string,
      driver: string
    },
    readyTitle: string;
    readySubtitle: string;
    btns: {
      bookNow: string,
      callUs: string
    }
  };
  locale: string;
};

export default function HomeUI({ booking_data, locale }: BookingSectionProps) {
  const isRTL = locale === "ar";
  const steps = [
    {
      icon: <MapPin className="w-6 h-6" />,
      title: booking_data.howToWork[0].title,
      desc: booking_data.howToWork[0].desc,
      color: "bg-blue-500"
    },
    {
      icon: <Calendar className="w-6 h-6" />,
      title: booking_data.howToWork[1].title,
      desc: booking_data.howToWork[1].desc,
      color: "bg-green-500"
    },
    {
      icon: <Users className="w-6 h-6" />,
      title: booking_data.howToWork[2].title,
      desc: booking_data.howToWork[2].desc,
      color: "bg-purple-500"
    },
    {
      icon: <CheckCircle className="w-6 h-6" />,
      title: booking_data.howToWork[3].title,
      desc: booking_data.howToWork[3].desc,
      color: "bg-primary"
    }
  ];

  return (
    <>
      <section className={`w-full py-20 lg:py-32 bg-gradient-to-br from-gray-50 via-white to-gray-50 ${isRTL ? 'rtl' : 'ltr'}`}>
        <div className="w-full">
          {/* Header */}
          <div className="text-center mb-20 px-6 md:px-12 xl:px-20">
            <Badge variant="outline" className="text-primary border-primary/20 mb-4">
              {booking_data.booking_title.span}
            </Badge>
            <h2 className="text-4xl text-black lg:text-5xl font-bold mb-6">
              {booking_data.booking_title.title}
              <span className="text-primary">{booking_data.booking_title.titlespan}</span>
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              {booking_data.booking_title.subtitle}
            </p>
          </div>

          {/* How It Works Steps */}
          <div className="mb-38 px-6 md:px-12 xl:px-20">
            {!isRTL && <h3 className="text-3xl text-black font-bold text-center mb-12">How It Works</h3>}
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
              {steps.map((step, index) => (
                <div key={index} className="relative">
                  <Card className="border-0 shadow-lg shadow-primary hover:shadow-xl transition-all duration-300 hover:scale-105 h-full">
                    <CardContent className="p-8 text-center">
                      <div className={`w-16 h-16 bg-black rounded-full flex items-center justify-center mx-auto mb-6 text-primary shadow-lg`}>
                        {step.icon}
                      </div>
                      <div className="absolute -top-3 -right-3 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm font-bold">
                        {index + 1}
                      </div>
                      <h4 className="text-xl font-bold mb-3">{step.title}</h4>
                      <p className="text-gray-600">{step.desc}</p>
                    </CardContent>
                  </Card>

                  {/* Connecting Arrow */}
                  {index < steps.length - 1 && !isRTL && (
                    <div className="hidden lg:block absolute top-1/2 -right-4 transform -translate-y-1/2 z-10">
                      <ArrowRight className={`w-6 h-6 text-gray-400 ${isRTL ? 'rotate-180' : ''}`} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* <div className="bg-foreground mb-28 py-28">
          <div className="flex items-center justify-center flex-col w-full">
            <div className="relative w-full h-[190px] md:me-auto">
              <Image
                src="/images/logo-witn-text.png"
                alt="landing_image"
                fill
                className="object-contain"
                quality={100}
                priority
              />
            </div>
              <div className="space-y-5">
                <div className="relative w-[220px] h-[120px] mx-auto">
                  <Image
                    src="/images/button-signup.png"
                    alt="signup_button"
                    fill
                    className="object-contain"
                    quality={100}
                    priority
                  />
                </div>
                <div className="flex items-end justify-end gap-10">
                  <Link href={`/${locale}/auth/`}>
                    <Button className="text-lg p-6 cursor-pointer">
                      Passenger
                    </Button>
                  </Link>{" "}
                  <Link href={`/${locale}/auth?captain=1`}>
                    <Button className="text-lg p-6 cursor-pointer">
                      PCO Driver
                    </Button>
                  </Link>{" "}
                </div>
              </div>
          </div>
          <div className="relative w-full lg:h-[330px] md:h-[250px] h-[200px]">
            <Image
              src="/images/car-main.png"
              alt="car_image"
              fill
              className="object-contain"
              quality={100}
              priority
            />
          </div>
        </div> */}
          <section className="bg-foreground text-white mb-28 py-20 md:py-32">
            <div className="container mx-auto px-4 flex flex-col items-center gap-12 xl:flex-row  xl:justify-between xl:items-start text-center">
              <div className="flex flex-col items-center ">
                <div className="relative w-[220px] h-[120px] mx-auto mb-8">
                  <Image
                    src="/images/button-signup.png"
                    alt="SIGN UP!"
                    fill
                    className="object-contain"
                    quality={100}
                    priority
                  />
                </div>
                <h1 className="text-3xl md:text-5xl font-bold tracking-tight">
                  {booking_data.joinUs.title}
                </h1>
                <p className="mt-4 max-w-lg text-base md:text-lg text-foreground-200">
                  {booking_data.joinUs.subtitle}
                </p>
                <div className="flex items-center gap-6 mt-6">
                  <Link href={`/${locale}/auth/`}>
                    <Button size="lg" className="text-lg px-8 py-6 cursor-pointer border-none">
                      {booking_data.joinUs.passenger}
                    </Button>
                  </Link>
                  <Link href={`/${locale}/auth?captain=1`}>
                    <Button size="lg" variant="outline" className="text-black text-lg px-8 py-6 cursor-pointer border-none hover:text-white">
                      {booking_data.joinUs.driver}
                    </Button>
                  </Link>
                </div>
              </div>

              <div className="max-w-[650px]">
                <Image src={DriverPic} alt="driver" className="sepia-50" />
              </div>

            </div>
          </section>

          {/* Services Z-Pattern Section */}
          <div className="space-y-32 mb-20 px-6 md:px-12 xl:px-20">
            {/* Header */}
            <div className="text-center mb-11">
              <h3 className="text-3xl text-black lg:text-4xl font-bold mb-4">{booking_data?.services?.title}</h3>
              <p className="text-gray-600 text-lg max-w-2xl mx-auto">
                {booking_data?.services?.subtitle}
              </p>
            </div>

            {/* First Row - Services on left, Image on right */}
            <div className={`grid lg:grid-cols-2 gap-16 items-center ${isRTL ? 'lg:grid-cols-2' : ''}`}>
              <div className={`space-y-8 ${isRTL ? 'lg:order-2' : ''}`}>
                <div className="space-y-6">
                  {booking_data.sections.slice(0, 3).map((section, index) => (
                    <Card key={index} className="border-l-4 border-l-primary border-t-0 border-r-0 border-b-0 shadow-md hover:shadow-lg transition-all duration-300 bg-gradient-to-r from-primary/5 to-transparent">
                      <CardContent className="p-6">
                        <div className="flex gap-4">
                          <div className="flex-shrink-0 w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white font-bold text-sm">
                            {index + 1}
                          </div>
                          <div className="flex-1">
                            <h4 className="text-xl font-bold mb-3 text-gray-900">{section.title}</h4>
                            <p className="text-gray-600 leading-relaxed">{section.text}</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>

              <div className={`relative ${isRTL ? 'lg:order-1' : ''}`}>
                <div className="relative w-full aspect-[4/2.65] rounded-3xl overflow-hidden shadow-2xl">
                  <Image
                    src={ServiceImage2}
                    alt="Premium transport service"
                    fill
                    className="object-contain sepia-50"
                    sizes="(max-width: 768px) 100vw, 50vw"
                    quality={100}
                  />
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-blue-500/10"></div>
                </div>

                {/* Decorative Elements */}
                <div className={`absolute -top-4 ${isRTL ? '-left-4' : '-right-4'} w-32 h-32 bg-primary/10 rounded-full blur-2xl`}></div>
                <div className={`absolute -bottom-4 ${isRTL ? '-left-4' : '-right-4'} w-24 h-24 bg-yellow-500/10 rounded-full blur-xl`}></div>
              </div>
            </div>

            {/* Second Row - Image on left, Benefits on right */}
            <div className={`grid lg:grid-cols-2 gap-16 items-center ${isRTL ? 'lg:grid-cols-2' : ''}`}>
              <div className={`relative ${isRTL ? 'lg:order-2' : ''}`}>
                <div className="relative w-full aspect-[4/2.65] rounded-3xl overflow-hidden shadow-2xl">
                  <Image
                    src={ServiceImage1}
                    alt="Professional chauffeur service"
                    fill
                    className="object-contain sepia-50"
                    sizes="(max-width: 768px) 100vw, 50vw"
                    quality={100}
                  />
                  <div className="absolute inset-0 bg-gradient-to-bl from-blue-500/10 via-transparent to-primary/10"></div>
                </div>

                {/* Decorative Elements */}
                <div className={`absolute -bottom-4 ${isRTL ? '-right-4' : '-left-4'} w-28 h-28 bg-green-500/10 rounded-full blur-xl`}></div>
              </div>

              <div className={`space-y-8 ${isRTL ? 'lg:order-1' : ''}`}>
                <div className="space-y-6">
                  {booking_data.sections.slice(3).map((section, index) => (
                    <Card key={index} className="border-l-4 border-l-primary border-t-0 border-r-0 border-b-0 shadow-md hover:shadow-lg transition-all duration-300 bg-gradient-to-r from-primary/5 to-transparent">
                      <CardContent className="p-6">
                        <div className="flex gap-4">
                          <div className="flex-shrink-0 w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white font-bold text-sm">
                            {index + 4}
                          </div>
                          <div className="flex-1">
                            <h4 className="text-xl font-bold mb-3 text-gray-900">{section.title}</h4>
                            <p className="text-gray-600 leading-relaxed">{section.text}</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </div>
          </div>

                {/* Popular Airport Transfers SEO Section */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl lg:text-4xl font-bold text-black mb-4">
              Popular Airport Transfers
            </h2>
            <p className="text-gray-600 max-w-2xl mx-auto text-lg">
              Reliable airport taxi and chauffeur services across London with professional drivers, fixed pricing, and 24/7 availability.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">

            <Card className="shadow-md hover:shadow-xl transition-all duration-300 border border-gray-100">
              <CardContent className="p-6 space-y-4">
                <h3 className="text-2xl font-bold text-black">
                  Heathrow Airport Transfer
                </h3>
                <p className="text-gray-600">
                  Executive and standard Heathrow airport transfers with meet and greet service, flight monitoring, and professional drivers.
                </p>
                <Link href={`/${locale}/heathrow-airport-transfer`}>
                  <Button className="cursor-pointer">
                    View Heathrow Transfers
                  </Button>
                </Link>
              </CardContent>
            </Card>

            <Card className="shadow-md hover:shadow-xl transition-all duration-300 border border-gray-100">
              <CardContent className="p-6 space-y-4">
                <h3 className="text-2xl font-bold text-black">
                  Gatwick Airport Transfer
                </h3>
                <p className="text-gray-600">
                  Comfortable Gatwick airport taxi services for business and leisure travel with fixed fares and reliable pickups.
                </p>
                <Link href={`/${locale}/gatwick-airport-transfer`}>
                  <Button className="cursor-pointer">
                    View Gatwick Transfers
                  </Button>
                </Link>
              </CardContent>
            </Card>

            <Card className="shadow-md hover:shadow-xl transition-all duration-300 border border-gray-100">
              <CardContent className="p-6 space-y-4">
                <h3 className="text-2xl font-bold text-black">
                  Stansted Airport Transfer
                </h3>
                <p className="text-gray-600">
                  Professional Stansted airport transfer services with punctual drivers and easy online booking across London.
                </p>
                <Link href={`/${locale}/stansted-airport-transfer`}>
                  <Button className="cursor-pointer">
                    View Stansted Transfers
                  </Button>
                </Link>
              </CardContent>
            </Card>

            <Card className="shadow-md hover:shadow-xl transition-all duration-300 border border-gray-100">
              <CardContent className="p-6 space-y-4">
                <h3 className="text-2xl font-bold text-black">
                  Luton Airport Transfer
                </h3>
                <p className="text-gray-600">
                  Affordable and executive Luton airport taxi services available 24 hours a day with experienced chauffeurs.
                </p>
                <Link href={`/${locale}/luton-airport-transfer`}>
                  <Button className="cursor-pointer">
                    View Luton Transfers
                  </Button>
                </Link>
              </CardContent>
            </Card>

            <Card className="shadow-md hover:shadow-xl transition-all duration-300 border border-gray-100">
              <CardContent className="p-6 space-y-4">
                <h3 className="text-2xl font-bold text-black">
                  London City Airport Transfer
                </h3>
                <p className="text-gray-600">
                  Fast and reliable London City Airport transfers for corporate and private passengers across Greater London.
                </p>
                <Link href={`/${locale}/london-city-airport-transfer`}>
                  <Button className="cursor-pointer">
                    View London City Transfers
                  </Button>
                </Link>
              </CardContent>
            </Card>

          </div>
        </div>
      </section>
          
          {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-primary to-primary/80 text-foreground">
        <div className="container mx-auto px-6 text-center">
          <div className="max-w-3xl mx-auto space-y-8">
            <h2 className="text-3xl lg:text-4xl font-bold">
              {booking_data.readyTitle}
            </h2>
            <p className="text-xl opacity-90">
              {booking_data.readySubtitle}
            </p>
            <div className="flex gap-4 justify-center flex-wrap">
              <Link href={`#book-now`}>
                <Button size="lg" variant="secondary" className="px-8 cursor-pointer">
                  {booking_data.btns.bookNow}
                </Button>
              </Link>
              <Link href={`/${locale}/about-us#contact-us`}>
                <Button size="lg" variant="outline" className="px-8 border-white text-black hover:bg-white hover:text-primary cursor-pointer">
                  {booking_data.btns.callUs}
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
