import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Shield, Clock, Star, MapPin } from "lucide-react";
import Image from "next/image";
import React from "react";
import ContactUs from "@/components/_components/about/ContactUs";
import getTrans from "@/lib/translation";
import { Locale } from "../../../../../i18n.config";
import Link from "next/link";

type PageProps = {
  params: Promise<{ locale: Locale }>;
};

export default async function AboutPage({ params }: PageProps) {
  const locale = (await params).locale;
  const isRTL = locale === 'ar';
  const { about_us } = await getTrans(locale, 'home');

  const features = [
    {
      icon: <Shield className="w-6 h-6" />,
      title: about_us.whyUs.steps[0].title,
      desc: about_us.whyUs.steps[0].desc
    },
    {
      icon: <Clock className="w-6 h-6" />,
      title: about_us.whyUs.steps[1].title,
      desc: about_us.whyUs.steps[1].desc
    },
    {
      icon: <Star className="w-6 h-6" />,
      title: about_us.whyUs.steps[2].title,
      desc: about_us.whyUs.steps[2].desc
    },
    {
      icon: <MapPin className="w-6 h-6" />,
      title: about_us.whyUs.steps[3].title,
      desc: about_us.whyUs.steps[3].desc
    }
  ];

  return (
    <div className={`min-h-screen bg-gradient-to-br from-gray-50 to-white ${isRTL ? 'rtl' : 'ltr'}`}>
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-r from-primary/10 via-primary/5 to-transparent">
        <div className="absolute -z-10 inset-0 bg-grid-pattern opacity-5"></div>
        <div className="container mx-auto px-6 py-20 lg:py-32">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="space-y-4">
                <Badge variant="outline" className="text-primary font-bold border-primary/50">
                  {about_us.about_us_title}
                </Badge>
                <h1 className="text-4xl lg:text-6xl font-bold text-black leading-tight">
                  {about_us.company_description_1.title}
                  <span className="text-primary block">
                    {about_us.company_description_1.titlespan}
                  </span>
                </h1>
                <p className="text-xl text-gray-600 leading-relaxed">
                  {about_us.company_description_1.desc}
                </p>
              </div>

              <div className="flex gap-4 flex-wrap">
                <Link href={`/${locale}`}>
                  <Button size="lg" className="px-8 cursor-pointer">
                    {about_us.btns.bookNow}
                  </Button>
                </Link>
                <Link href={`#more`}>
                  <Button variant="outline" size="lg" className="px-8 text-black cursor-pointer hover:bg-secondary">
                    {about_us.btns.learnMore}
                  </Button>
                </Link>
              </div>
            </div>

            <div className="relative">
              <div className="relative w-full h-[400px] lg:h-[500px]">
                <Image
                  src="/images/logo.png"
                  alt="Airport & City Transfer"
                  fill
                  className="object-contain"
                  sizes="(max-width: 768px) 100vw, 50vw"
                  quality={100}
                  priority
                />
              </div>
              <div className="absolute -bottom-4 -right-4 w-24 h-24 bg-primary/10 rounded-full blur-xl"></div>
              <div className="absolute -top-4 -left-4 w-32 h-32 bg-yellow-500/10 rounded-full blur-xl"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 bg-foreground">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className=" text-white text-3xl lg:text-4xl font-bold mb-4">{about_us.whyUs.title}</h2>
            <p className="text-gray-500 text-lg max-w-2xl mx-auto">
              {about_us.whyUs.subtitle}
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <Card key={index} className="bg-white border-0 shadow-lg transition-all duration-300 hover:scale-105 shadow-primary hover:shadow-xl cursor-pointer">
                <CardContent className="p-6 text-center">
                  <div className="w-16 h-16 bg-yellow-50 rounded-full flex items-center justify-center mx-auto mb-6 text-primary border border-foreground">
                    {feature.icon}
                  </div>
                  <h3 className="text-xl font-bold mb-3 text-foreground leading-5">{feature.title}</h3>
                  <p className="text-sm font-medium text-foreground/60 leading-4">{feature.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Story Section */}
      <section className="py-20 bg-gray-50" id="more">
        <div className="container mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div className="space-y-8">
              <div className="space-y-6">
                <h2 className="text-black text-3xl lg:text-4xl font-bold">{about_us.ourStory}</h2>
                <div className="space-y-4 text-gray-600 leading-relaxed">
                  <p>
                    {about_us.company_description_2.desc1}{' '}
                    <span className="font-bold text-gray-900">
                      {about_us.company_description_2.desc2}
                    </span>
                    {about_us.company_description_2.desc3}
                  </p>
                  <p>{about_us.company_description_3}</p>
                  <p>{about_us.company_description_4}</p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-8 pt-8 border-t border-gray-200">
                <div className="text-center">
                  <div className="text-3xl font-bold text-primary mb-2">1000+</div>
                  <div className="text-sm text-gray-600">{about_us.customers}</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-primary mb-2">24/7</div>
                  <div className="text-sm text-gray-600">{about_us.available}</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-primary mb-2">5★</div>
                  <div className="text-sm text-gray-600">{about_us.rating}</div>
                </div>
              </div>
            </div>

            <div className="relative">
              <div className="relative w-full h-[400px] rounded-2xl overflow-hidden shadow-2xl shadow-foreground">
                <Image
                  src="/images/logo-about.png"
                  alt="About us"
                  fill
                  className="object-contain"
                  sizes="(max-width: 768px) 100vw, 50vw"
                  quality={100}
                />
              </div>
              <div className="absolute -bottom-8 -left-8 w-32 h-32 bg-primary/10 rounded-full blur-2xl"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section id="contact-us" className="py-20">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto">
            <div className="text-center">
              <h2 className="text-3xl lg:text-4xl text-black font-bold">
                {about_us.get_in_touch.title}
                <span className="text-primary"> {about_us.get_in_touch.titlespan}</span>
              </h2>
              <p className="text-gray-600 text-lg">
                {about_us.get_in_touch.subtitle}
              </p>
            </div>

            <Card className="shadow-xl border-0 p-0 max-w-3xl mx-auto my-7">
                <ContactUs form={about_us.get_in_touch.form} />
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      {/* <section className="py-20 bg-gradient-to-r from-primary to-primary/80 text-foreground">
        <div className="container mx-auto px-6 text-center">
          <div className="max-w-3xl mx-auto space-y-8">
            <h2 className="text-3xl lg:text-4xl font-bold">
              {about_us.readyTitle}
            </h2>
            <p className="text-xl opacity-90">
              {about_us.readySubtitle}
             </p>
            <div className="flex gap-4 justify-center flex-wrap">
              <Link href={`/${locale}`}>
                <Button size="lg" variant="secondary" className="px-8 cursor-pointer">
                  {about_us.btns.bookNow}
                </Button>
              </Link>
              <Link href={`#footer`}>
                <Button size="lg" variant="outline" className="px-8 border-white text-black hover:bg-white hover:text-primary cursor-pointer">
                  {about_us.btns.callUs}
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section> */}
    </div>
  );
}