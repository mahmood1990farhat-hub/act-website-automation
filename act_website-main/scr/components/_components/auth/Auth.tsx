"use client";
import React, { useEffect, useState } from "react";
import Login from "./Login";
import AdminLogin from "./AdminLogin";
import { Locale } from "../../../../i18n.config";
import SignUpT from "./SignUp";
import VerifyAccount from "./VerifyAccount";
import ForgotPasswordForm from "./ForgotPasswordForm";
import ResetPasswordForm from "./ResetPasswordForm";
import Image from "next/image";
import CreateCaptainAccount from "./captain/CreateCaptainAccount";
import GetStartedCaptain from "./captain/GetStartedCaptain";
import DriverOnboardingStep1 from "./captain/DriverOnboardingStep1";

type typeProps = {
  locale: Locale;
  trans: any;
  isCaptain?: string;
  isAdmin?: boolean;
  setStep?: () => void;
  isBookingFlow?: boolean;
};

export default function Auth({ locale, trans, isCaptain, isAdmin, setStep, isBookingFlow }: typeProps) {
  const [tap, setTap] = useState(1);
  const [sevePhoneforOTP, setSevePhoneforOTP] = useState("");

  // Listen for reset auth tab event
  useEffect(() => {
    const handleResetAuthTab = (event: CustomEvent) => {
      if (event.detail?.step) {
        setTap(event.detail.step);
      }
    };

    window.addEventListener('resetAuthTab', handleResetAuthTab as EventListener);
    
    return () => {
      window.removeEventListener('resetAuthTab', handleResetAuthTab as EventListener);
    };
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [tap]);

  useEffect(() => {
    if (isCaptain && !setStep) {
      setTap(8); // Driver onboarding Step 1
    } else if (setStep) {
      setTap(1);
    }
  }, [isCaptain, setStep]);

  const authSteps = [
    {
      key: "login",
      component: isAdmin ? (
        <AdminLogin
          locale={locale}
          trans={trans.admin_login}
          setStep={() => setStep?.()}
        />
      ) : (
        <Login
          setTapAction={setTap}
          locale={locale}
          trans={trans.login}
          setStep={() => setStep?.()}
          isCaptain={isCaptain}
          isBookingFlow={isBookingFlow}
        />
      ),
      img: "/images/login.png",
    },
    {
      key: "signup",
      component: (
        <SignUpT setTap={setTap} locale={locale} trans={trans.signup} isCaptain={isCaptain} setSevePhoneforOTP={(phone)=>setSevePhoneforOTP(phone)} />
      ),
      img: "/images/signup.png",
    },
    {
      key: "verify",
      component: (
        <VerifyAccount
        phone={sevePhoneforOTP}
          setTap={setTap}
          locale={locale}
          trans={trans.VerifyAccount}
        />
      ),
      img: "/images/otp.png",
    },
    {
      key: "forgot",
      component: (
        <ForgotPasswordForm 
          setTap={setTap} 
          trans={trans.forgot_password} 
          locale={locale}
        />
      ),
      img: "/images/ForgotPassword.png",
    },
    {
      key: "reset",
      component: (
        <ResetPasswordForm
          setTap={setTap}
          locale={locale}
          trans={trans.ResetPassword}
        />
      ),
      img: "/images/ResetPassword.png",
    },
  ];

  return (
    <div className="w-full min-h-screen bg-black bg-gradient py-6 md:py-10 pb-6 md:pb-10">
      {tap === 6 || tap === 7 || tap === 8 ? (
        <div className="w-full py-5">
          {tap === 8 ? (
            // Driver Onboarding Step 1
            <div className="flex-1 w-full flex justify-center bg-gray-900/80 backdrop-blur-sm px-6 md:px-12 lg:px-20 py-10 rounded-3xl max-w-[1000px] mx-auto border border-gray-700">
              <div className="w-full" dir={locale === "en" ? "ltr" : "rtl"}>
                <DriverOnboardingStep1
                  setTapAction={setTap}
                  locale={locale}
                  trans={trans.driverOnboarding || trans.signup}
                />
              </div>
            </div>
          ) : tap === 6 ? (
            <CreateCaptainAccount
              locale={locale}
              setTapAction={setTap}
              trans={trans.CreateCaptainAccount}
              transGetStarted={trans.GetStartedCaptain}
              transInfo={trans.signup}
            />
          ) : (
            <CreateCaptainAccount
              locale={locale}
              setTapAction={setTap}
              trans={trans.CreateCaptainAccount}
              transGetStarted={trans.GetStartedCaptain}
              transInfo={trans.signup}
            />
          )}
        </div>
      ) : (
        <div
          className="flex items-center gap-5 md:py-15 py-4 w-full lg:px-25 px-5 max-md:flex-col-reverse min-h-[calc(100vh-3rem)]"
          dir="ltr"
        >
          <div className="flex-1 w-full flex justify-center bg-gray-900/80 backdrop-blur-sm px-6 md:px-12 lg:px-28 py-18 rounded-3xl max-w-[800px] mx-auto border border-gray-700">
            <div className="w-full" dir={locale === "en" ? "ltr" : "rtl"}>
              {authSteps[tap - 1]?.component}
            </div>
          </div>
          {/* <div className="flex-1 w-full">
            <div className="relative w-full lg:h-[430px] md:h-[350px] h-[300px]">
              <Image
                src={authSteps[tap - 1].img}
                alt={authSteps[tap - 1].key}
                fill
                className="object-contain"
                quality={100}
                priority
              />
            </div>
          </div> */}
        </div>
      )}
    </div>
  );
}
