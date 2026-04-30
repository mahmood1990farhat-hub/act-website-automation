import React, { useEffect, useRef, useState } from "react";
import { Locale } from "../../../../i18n.config";
import { postData } from "@/lib/api/postData";
import { Button } from "@/components/ui/button";
import Image from "next/image";



export default function VerifyAccount({
  locale,
  trans,
  phone
}: {
  locale: Locale;
    setTap: (tep:number) => void;
  trans: any;
  phone:string
}) {
  


  const [otp, setOtp] = useState<string[]>(["", "", "", "", "", ""]);

  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);
  const [timeLeft, setTimeLeft] = useState(120);

  const handleOtpChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    idx: number
  ) => {
    const value = e.target.value;
    if (!/^\d*$/.test(value)) return;
    const newOtp = [...otp];
    newOtp[idx] = value;
    setOtp(newOtp);

    if (value && idx < otp.length - 1) {
      otpRefs.current[idx + 1]?.focus();
    }
  };

  const handleBackspace = (
    e: React.KeyboardEvent<HTMLInputElement>,
    idx: number
  ) => {
    if (e.key === "Backspace" && !otp[idx] && idx > 0) {
      otpRefs.current[idx - 1]?.focus();
    }
  };

  const handleResend = () => {
    setOtp(Array(6).fill(""));
    setTimeLeft(120);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
      .toString()
      .padStart(2, "0");
    const secs = (seconds % 60).toString().padStart(2, "0");
    return `${mins}:${secs}`;
  };

  useEffect(() => {
    if (timeLeft <= 0) return;
    const timer = setInterval(() => {
      setTimeLeft((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [timeLeft]);

  const onSubmitOtp = async () => {
    try {
      const res = await postData<any>({
        endpoint: `/api/auth/verify-otp/`,
        body: {  phone_number:phone,code: otp.join("") },
        queryParams: { locale: locale },
      });
    } catch (error) {
      console.log("Caught error:", error);
    }
  };

  return (

      <div className="space-y-10">
     <div>
       <h1 className="text-lg font-bold text-center py-1">{trans.enterOtp}</h1>
        <p className="text-sm text-center text-muted mb-4 px-10">
          {trans.otpSent}
        </p>

     </div>
        <div className="flex justify-between gap-2 mb-4" dir="ltr">
          {Array.from({ length: 6 }).map((_, idx) => (
            <input
              key={idx}
              type="text"
              maxLength={1}
              className="w-12 h-12 text-center text-xl border rounded bg-foreground focus:ring-2 focus:ring-popover"
              value={otp[idx] || ""}
              onChange={(e) => handleOtpChange(e, idx)}
              onKeyDown={(e) => handleBackspace(e, idx)}
              ref={(el) => {
                if (el) otpRefs.current[idx] = el;
              }}
            />
          ))}
        </div>

        <p className="text-sm text-center my-2 ">
          {timeLeft > 0 ? (
            <>
              {trans.otpNotReceived}
              <span
                className="underline text-primary cursor-pointer px-0.5"
                onClick={handleResend}
              >
                {trans.resend}
              </span>
              <br />
              <span className="font-bold text-secondary text-lg">
                {formatTime(timeLeft)}
              </span>
            </>
          ) : (
            <button
              type="button"
              onClick={handleResend}
              className=" text-primary underline cursor-pointer"
            >
              {trans.resend}
            </button>
          )}
        </p>

        <Button
          type="submit"
          onClick={onSubmitOtp}
          className="text-2xl w-full p-6"
        >
          {trans.confirmBtn}
        </Button>
      </div>

  );
}
