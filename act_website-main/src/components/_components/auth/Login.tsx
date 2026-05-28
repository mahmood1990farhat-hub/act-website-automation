"use client";
import { useState, useEffect } from "react";
import { useForm, SubmitHandler } from "react-hook-form";
import { postData } from "@/lib/api/postData";
import { deleteCookie, setCookie } from "cookies-next";
import { Button } from "@/components/ui/button";
import PasswordField from "./PasswordField";
import InputField from "./InputField";

import { IoMail } from "react-icons/io5";
import { FaUserAlt, FaCar } from "react-icons/fa";
import { useRouter } from "next/navigation";
import GlobalModal from "../GlobalModal";
import { toast } from "react-toastify";
import CarLoading from "../loading/CarLoading";

type LoginData = {
  username: string;
  password: string;
  email?: string;
};

export default function Login({
  setTapAction,
  locale,
  trans,
  setStep,
  isCaptain,
  isBookingFlow,
}: {
  setTapAction: (tep: number) => void;
  locale: string;
  trans: any;
  setStep?: () => void;
  isCaptain?: string;
  isBookingFlow?: boolean;
}) {
  const [showPassword, setShowPassword] = useState(false);
  const [adminVerified, setAdminVerified] = useState(false);
  const [loading, setIsLoading] = useState(false);
  const [loginType, setLoginType] = useState<"passenger" | "driver">(
    isCaptain ? "driver" : "passenger"
  );
  const router = useRouter();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginData>();

  // Update loginType when isCaptain prop changes
  useEffect(() => {
    // If booking flow, always use passenger login
    if (isBookingFlow) {
      setLoginType("passenger");
    } else if (isCaptain === "true" || isCaptain === "1") {
      setLoginType("driver");
    } else {
      setLoginType("passenger");
    }
  }, [isCaptain, isBookingFlow]);

  const notifyAuthChange = () => {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("authStateChanged"));
    }
  };

  const onSubmit: SubmitHandler<LoginData> = async (data) => {
    setIsLoading(true);
    try {
      // Use different endpoints based on selected login type
      const endpoint = loginType === "driver" 
        ? "/api/drivers/login/" 
        : "/api/auth/login/";
      
      // Driver login uses email field, normal login uses username
      const body = loginType === "driver"
        ? {
            email: data.username, // Using username field as email for drivers
            password: data.password,
            account_type: "driver",
          }
        : {
            username: data.username,
            password: data.password,
            account_type: "passenger",
          };

      const res = await postData<any>({
        endpoint: endpoint,
        body: body,
        queryParams: {
          locale,
        },
      });
      // Debug: Log the response to see what we're getting
      
      
      // Extract values from response
      const isAdminVerified = res.user?.is_admin_verified;
      const userId = res.user?.id || res.user_id;
      const onboardingStatus = res.onboarding_status;
      
      // Debug logging - store in localStorage so it persists after redirect
      const debugInfo = {
        isAdminVerified,
        onboardingStatus,
        accountType: loginType === "driver" ? "normal_driver" : res.account_type,
        timestamp: new Date().toISOString()
      };
      console.log("Login response:", debugInfo);
      if (typeof window !== "undefined") {
        localStorage.setItem("driver_login_debug", JSON.stringify(debugInfo));
      }
      
      // Determine account type based on which API we called
      const accountType = loginType === "driver" ? "normal_driver" : res.account_type;
      
      // VALIDATION: For passenger login attempts, discard action if account type is not passenger
      if (loginType === "passenger" && accountType !== "passenger") {
        toast.error("Please use the correct login form for your account type. This appears to be a driver account.");
        setIsLoading(false);
        return; // Discard any further action
      }
      
      // Set basic cookies for all users
      setCookie("userToken", res.access_token, { maxAge: 60 * 60 * 24 });
      setCookie("user_id", userId, { maxAge: 60 * 60 * 24 });
      setCookie("account_type", accountType, { maxAge: 60 * 60 * 24 });
      
      // Save user info to cookies for profile display
      if (res.first_name) setCookie("user_first_name", res.first_name, { maxAge: 60 * 60 * 24 });
      if (res.last_name) setCookie("user_last_name", res.last_name, { maxAge: 60 * 60 * 24 });
      if (res.email) setCookie("user_email", res.email, { maxAge: 60 * 60 * 24 });
      if (res.phone_number) setCookie("user_phone_number", res.phone_number, { maxAge: 60 * 60 * 24 });
      if (res.user?.phone_number) setCookie("user_phone_number", res.user.phone_number, { maxAge: 60 * 60 * 24 });
      
      notifyAuthChange();
      
      // Handle different account types
      switch (accountType) {
        case "normal":
          // Admin user - set access token and redirect to dashboard
          if (isBookingFlow && setStep) {
            // Booking flow - close auth modal
            setStep();
            setIsLoading(false);
            return; // Exit early if in booking flow
          }
          // Normal admin login - redirect to dashboard with hard redirect
          // Keep loading true until redirect completes
          if (typeof window !== "undefined") {
            window.location.href = `/${locale}/dashboard/overview`;
          }
          // Don't set loading to false - let the redirect happen
          return; // keep loading until navigation
          
        case "normal_driver": {
          // Driver user - set admin verification cookie
          setCookie("is_admin_verified", isAdminVerified, { maxAge: 60 * 60 * 24 });

          // Check for needs_modification status first (before other checks)
          const needsModification = onboardingStatus?.status === "needs_modification" || 
                                    onboardingStatus?.status === "needs modification" ||
                                    String(onboardingStatus?.status).toLowerCase().includes("needs_modification");
          
          const driverDebugInfo = {
            isAdminVerified,
            onboardingStatus,
            needsModification,
            statusValue: onboardingStatus?.status,
            fullOnboardingStatus: JSON.stringify(onboardingStatus),
            timestamp: new Date().toISOString()
          };
          
          console.log("Driver login check:", driverDebugInfo);
          
          // Store in localStorage for debugging
          if (typeof window !== "undefined") {
            localStorage.setItem("driver_login_debug_check", JSON.stringify(driverDebugInfo));
          }
          
          // Debug: Log to console and localStorage
          if (typeof window !== "undefined" && onboardingStatus) {
            console.log(`DEBUG: Status=${onboardingStatus?.status}, NeedsMod=${needsModification}`);
          }

          if (isAdminVerified === true) {
            toast.info(
              trans?.driverAppOnlyMessage ||
                "Your driver account is verified. Please use the Driver mobile app to log in. Web access is only for onboarding.",
              {
                autoClose: 8000,
              }
            );

            ["userToken", "user_id", "account_type", "is_admin_verified"].forEach((cookieName) =>
              deleteCookie(cookieName)
            );

            router.push(`/${locale}/download-app`);
            router.refresh();
            return; // keep loading until navigation
          } else if (needsModification) {
            // Documents need modification - redirect to upload-documents page
            console.log("✅ Needs modification detected, redirecting to upload-documents");
            if (typeof window !== "undefined") {
              localStorage.setItem("driver_login_action", "redirecting_to_upload_documents");
              
              // Verify cookies are set before redirecting
              const verifyAndRedirect = () => {
                const tokenCookie = document.cookie.split(';').find(c => c.trim().startsWith('userToken='));
                const accountTypeCookie = document.cookie.split(';').find(c => c.trim().startsWith('account_type='));
                
                console.log("Cookie check:", {
                  hasToken: !!tokenCookie,
                  hasAccountType: !!accountTypeCookie,
                  accountType: accountTypeCookie?.split('=')[1]
                });
                
                if (tokenCookie && accountTypeCookie) {
                  console.log("🚀 Cookies verified, executing redirect to upload-documents");
                  window.location.replace(`/${locale}/upload-documents`);
                } else {
                  console.log("⏳ Cookies not ready, retrying...");
                  setTimeout(verifyAndRedirect, 100);
                }
              };
              
              // Start verification after a short delay
              setTimeout(verifyAndRedirect, 200);
            }
            return; // keep loading until redirect
          } else if (onboardingStatus?.can_upload_documents === true) {
            // Step 1 approved - show document upload form
            setTapAction(7); // This shows CreateCaptainAccount component
            setIsLoading(false);
          } else {
            // Pending review - show dialog and redirect to home page
            setAdminVerified(true);
            setIsLoading(false);
            setTimeout(() => {
              setAdminVerified(false);
              // router.push(`/${locale}`);
              router.refresh();
            }, 15000);
          }
          break;
        }
          
        case "passenger":
        default:
          setCookie("userToken", res.access_token, { maxAge: 60 * 60 * 24 });
          
          // Save user info to cookies for profile display
          if (res.first_name) setCookie("user_first_name", res.first_name, { maxAge: 60 * 60 * 24 });
          if (res.last_name) setCookie("user_last_name", res.last_name, { maxAge: 60 * 60 * 24 });
          if (res.email) setCookie("user_email", res.email, { maxAge: 60 * 60 * 24 });
          if (res.phone_number) setCookie("user_phone_number", res.phone_number, { maxAge: 60 * 60 * 24 });
          if (res.user?.phone_number) setCookie("user_phone_number", res.user.phone_number, { maxAge: 60 * 60 * 24 });
          
          notifyAuthChange();

          if (isBookingFlow && setStep) {
            // Booking flow - close auth modal and continue to payment
            setStep();
            setIsLoading(false);
            return; // Exit early, don't redirect
          } else {
            // Normal login - redirect to home with hard redirect
            // Keep loading true until redirect completes
            if (typeof window !== "undefined") {
              window.location.href = `/${locale}`;
            }
            // Don't set loading to false - let the redirect happen
            return; // Exit after redirect
          }
      }
    } catch (error) {
      console.error("Login Error:", error);
      setIsLoading(false);
    }
  };

  return (
    <div className="relative w-full">
      <GlobalModal
        isOpen={adminVerified}
        onClose={() => setAdminVerified(false)}
      >
        <div className="relative w-full max-w-md mx-auto p-6">
          {/* Close Button */}
          <button
            onClick={() => setAdminVerified(false)}
            className="absolute top-3 right-3 text-gray-400 hover:text-white transition-colors z-10"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          
          {/* Header */}
          <div className="text-center mb-6">
            {/* Icon */}
            <div className="w-16 h-16 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            
            {/* Title */}
            <h2 className="text-xl font-bold text-white mb-2">
              {trans.pendingRequest || "Application Under Review"}
            </h2>
            
            {/* Subtitle */}
            <p className="text-sm text-gray-300">
              Your driver application is being processed
            </p>
          </div>
          
          {/* Content */}
          <div className="space-y-4">
            {/* Main Message */}
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
              <p className="text-sm text-gray-300 leading-relaxed">
                Our compliance team is reviewing your documents and information to ensure you meet all requirements.
              </p>
            </div>
            
            {/* Timeline */}
            <div className="bg-gray-800/30 border border-gray-700/50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-blue-300 font-medium text-sm">Processing Timeline</p>
              </div>
              <p className="text-xs text-gray-300">
                24-48 hours • Email notification will be sent
              </p>
            </div>
            
            {/* Process Steps */}
            <div className="bg-gray-800/30 border border-gray-700/50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-3">
                <svg className="w-4 h-4 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <p className="text-gray-200 font-medium text-sm">Next Steps</p>
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 bg-green-400 rounded-full"></div>
                  <span className="text-xs text-gray-300">Document verification</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full"></div>
                  <span className="text-xs text-gray-300">Background check</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 bg-blue-400 rounded-full"></div>
                  <span className="text-xs text-gray-300">Account activation</span>
                </div>
              </div>
            </div>
          </div>
          
          {/* Footer */}
          <div className="mt-6 text-center">
            <p className="text-xs text-gray-400 bg-gray-800/50 px-3 py-2 rounded-lg">
              Redirecting to home page...
            </p>
          </div>
        </div>
      </GlobalModal>
      <h1 className="text-3xl lg:text-5xl mb-3 font-extrabold text-center py-1">{trans.title}</h1>
      <p className="text-muted text-center mt-1 mb-6 w-full">
        {trans.desc_main}
      </p>

      {/* Login Type Switcher - Hide driver tab in booking flow */}
      {!isBookingFlow && (
        <div className="flex items-center gap-2 p-1 bg-muted/30 rounded-lg mb-6">
          <button
            type="button"
            onClick={() => setLoginType("passenger")}
            className={`flex-1 py-3 px-4 rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2 ${
              loginType === "passenger"
                ? "bg-primary text-foreground shadow-lg"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <FaUserAlt className="text-base" /> {trans.passenger || "Passenger"}
          </button>
          <button
            type="button"
            onClick={() => setLoginType("driver")}
            className={`flex-1 py-3 px-4 rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2 ${
              loginType === "driver"
                ? "bg-primary text-foreground shadow-lg"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <FaCar className="text-base h-5 w-5" /> {trans.driver || "Driver"}
          </button>
        </div>
      )}

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4 text-sm  w-full"
      >
        <InputField
          label={loginType === "driver" ? trans.email || "Email" : trans.usernameMail}
          placeholder={
            loginType === "driver" 
              ? trans.emailPlaceholder || "your-email@example.com"
              : trans.usernamePlaceholder || "xxxxxxxx@gmail.com"
          }
          register={register}
          name="username"
          requiredMsg={
            loginType === "driver" 
              ? trans.emailRequired || "Email is required"
              : trans.usernameRequired
          }
          error={errors.username}
          type={loginType === "driver" ? "email" : "text"}
          icon={<IoMail className="mx-2 text-lg " />}
        />

        <div>
          <PasswordField
            label={trans.passwordLabel}
            name="password"
            register={register}
            show={showPassword}
            setShow={setShowPassword}
            validate={{
              required: trans.passwordRequired,
              minLength: { value: 4, message: trans.passwordRequired },
            }}
            error={errors.password}
          />
          <div
            onClick={() => setTapAction(4)}
            className="flex items-center ms-auto  underline text-gray-300 text-sm cursor-pointer"
          >
            {trans.forgotPassword}
          </div>
        </div>

        <Button type="submit" className="text-2xl w-full p-6 cursor-pointer" disabled={loading}>
          {trans.loginButton}
        </Button>
      </form>

      <p className="text-center text-sm mt-4 text-muted">
        {loginType === "driver" ? (
          <>
            {trans.newDriver || "New driver?"}{" "}
            <span
              onClick={() => setTapAction(8)}
              className="text-primary px-1 underline cursor-pointer"
            >
              {trans.applyNow || "Apply Now"}
            </span>
          </>
        ) : (
          <>
            {trans.noAccount}{" "}
            <span
              onClick={() => setTapAction(2)}
              className="text-primary px-1 underline cursor-pointer"
            >
              {trans.signup}
            </span>
          </>
        )}
      </p>
      {loading && (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 backdrop-blur-sm rounded-lg"
          aria-busy="true"
          aria-live="assertive"
        >
          <div className="flex flex-col items-center gap-4 px-6 py-8 bg-foreground/95 backdrop-blur-md rounded-2xl border border-primary/20 shadow-2xl">
            <CarLoading />
            <p className="text-sm text-white/80">
              {loginType === "driver"
                ? "Signing you in to your driver account..."
                : "Signing you in to your account..."}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
