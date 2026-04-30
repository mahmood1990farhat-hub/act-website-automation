import React from "react";
import { IoIosCheckmarkCircle } from "react-icons/io";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { booking_Confirmation } from ".";
import { Locale } from "../../../../i18n.config";

type typeProps = {
  trans: booking_Confirmation;
  locale: Locale;
};

export default function BookingConfirmation({ trans, locale }: typeProps) {
  const isRTL = locale === 'ar';
  const urlMytrip = trans.desc.hour === " 1 " ? "/en/my-trips" : "/ar/my-trips";

  return (
    <div className="min-h-screen bg-white/10 backdrop-blur-sm flex items-center justify-center p-8 rounded-2xl max-sm:p-1">
      <div className="w-full max-w-md">

        {/* Main Content Card */}
        <div className="bg-foreground rounded-2xl shadow-xl overflow-hidden">
          {/* Header */}
          <div className="space-y-3.5 bg-primary px-6 py-8 text-center">
            <IoIosCheckmarkCircle className="text-6xl text-foreground mx-auto" />
            <h1 className="text-2xl font-bold text-foreground mb-2">
              {trans.title}
            </h1>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Booking Details */}
            <div className="text-center space-y-2">
              <div className="text-white text-base leading-relaxed">
                <span>{trans.desc.span_1}</span>
                <span className="font-semibold text-foreground bg-emerald-50 px-2 py-1 rounded-md mx-1">
                  {trans.desc.hour.trim()}
                </span>
                <span>{trans.desc.span_2}</span>
              </div>
            </div>

            {/* Divider */}
            <div className="flex items-center space-x-4">
              <div className="flex-1 h-px bg-gray-200"></div>
              <div className="text-xs text-gray-400 font-medium">NEXT STEPS</div>
              <div className="flex-1 h-px bg-gray-200"></div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-3">
              <Link href={urlMytrip} className="block w-full">
                <Button className="w-full bg-primary text-foreground font-semibold py-4 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 transform hover:-translate-y-0.5 cursor-pointer">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  {trans.button}
                </Button>
              </Link>

              <Button
                onClick={() => location.reload()}
                className="w-full bg-foreground border-2 border-primary text-white/90 font-semibold py-4 rounded-xl transition-all duration-200 transform hover:-translate-y-0.5 cursor-pointer hover:bg-transparent"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                {trans.button_Back_to_home}
              </Button>
            </div>

            {/* Additional Info */}
            {!isRTL && <div className="rounded-xl p-4 text-center">
              <p className="text-xs text-muted leading-none">
                Confirmation details sent to your email
              </p>
              <p className="text-xs text-muted mt-1">
                Need help? Contact our support team 24/7
              </p>
            </div>}
          </div>
        </div>

        {/* Decorative Elements */}
        <div className="flex justify-center mt-6 space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
          <div className="w-2 h-2 bg-primary rounded-full animate-pulse delay-100"></div>
          <div className="w-2 h-2 bg-primary rounded-full animate-pulse delay-200"></div>
        </div>
      </div>
    </div>
  );
}