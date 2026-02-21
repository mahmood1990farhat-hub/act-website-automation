"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { deleteCookie, getCookie } from "cookies-next";
import { toast } from "react-toastify";
import { Locale } from "../../../../i18n.config";
import GlobalModal from "../GlobalModal";
import { Button } from "@/components/ui/button";
import { BsEyeFill, BsEyeSlashFill } from "react-icons/bs";
import {
  HiOutlineTrash,
  HiOutlineKey,
  HiOutlineDevicePhoneMobile,
  HiOutlineArrowLeftStartOnRectangle,
} from "react-icons/hi2";
import ChangePasswordForm from "./ChangePasswordForm";
import ChangeEmailForm from "./ChangeEmailForm";
import ChangePhoneForm from "./ChangePhoneForm";
import { postData } from "@/lib/api/postData";
import { HiOutlineMail } from "react-icons/hi";

type ProfileProps = {
  locale: Locale;
  trans: any;
  accountType?: string;
};

type UserInfo = {
  id?: number;
  email?: string;
  phone_number?: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  username?: string;
  [key: string]: any;
};

export default function Profile({ locale, trans, accountType = "passenger" }: ProfileProps) {
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showChangePasswordDialog, setShowChangePasswordDialog] = useState(false);
  const [showChangeEmailDialog, setShowChangeEmailDialog] = useState(false);
  const [showChangePhoneDialog, setShowChangePhoneDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [changePasswordTrans, setChangePasswordTrans] = useState<any>(null);
  const [changeEmailTrans, setChangeEmailTrans] = useState<any>(null);
  const [changePhoneTrans, setChangePhoneTrans] = useState<any>(null);
  const router = useRouter();
  const token = getCookie("userToken") as string;

  // Load translations
  useEffect(() => {
    const loadTranslations = async () => {
      try {
        const authTrans = await import(`@/dictionaries/${locale}/auth.json`).then(
          (module) => module.default
        );
        setChangePasswordTrans(authTrans.ChangePassword);
        setChangeEmailTrans(authTrans.ChangeEmail || {});
        setChangePhoneTrans(authTrans.ChangePhone || {});
      } catch (error) {
        console.error("Error loading translations:", error);
      }
    };
    loadTranslations();
  }, [locale]);

  // Load user info from cookies (saved during login)
  useEffect(() => {
    if (!token) return;

    setIsLoading(true);
    try {
      // Get user info from cookies saved during login
      const userInfoFromCookies: UserInfo = {
        first_name: getCookie("user_first_name") as string || undefined,
        last_name: getCookie("user_last_name") as string || undefined,
        email: getCookie("user_email") as string || undefined,
        phone_number: getCookie("user_phone_number") as string || undefined,
      };

      if (userInfoFromCookies.first_name || userInfoFromCookies.email) {
        setUserInfo(userInfoFromCookies);
      }
    } catch (error) {
      console.error("Error loading user info from cookies:", error);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  const notifyAuthChange = () => {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("authStateChanged"));
    }
  };


  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      const cookiesToClear = [
        "userToken",
        "user_id",
        "account_type",
        "is_admin_verified",
      ];

      cookiesToClear.forEach((cookieName) => deleteCookie(cookieName));
      setShowLogoutDialog(false);
      notifyAuthChange();

      router.push(`/${locale}`);
      router.refresh();
      toast.success(trans.logoutSuccess || "Logged out successfully");
    } catch (error) {
      toast.error(trans.logoutError || "Error during logout");
    } finally {
      setIsLoggingOut(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!password.trim()) {
      toast.error(trans.passwordRequired);
      return;
    }

    setIsDeleting(true);
    try {
      await postData({
        endpoint: "/api/auth/delete-account/",
        token: token,
        body: { password, action: "delete" },
        noToast: true,
      });

      const cookiesToClear = [
        "userToken",
        "user_id",
        "account_type",
        "is_admin_verified",
      ];

      cookiesToClear.forEach((cookieName) => deleteCookie(cookieName));
      setShowDeleteDialog(false);
      setPassword("");
      setShowPassword(false);
      notifyAuthChange();
      router.push(`/${locale}`);
      router.refresh();
      // Success toast is handled by postData
    } catch (error) {
      // Error toast is handled by postData
    } finally {
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-lg text-white">{trans.loading || "Loading..."}</div>
      </div>
    );
  }

  return (
    <>
      <div className="w-full space-y-6">
        {/* Profile Header */}
        
        <div className="bg-foreground/50 backdrop-blur-sm rounded-xl shadow-lg border border-muted/10 p-6">
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-white">
              {trans.title || "Profile"}
            </h1>
          </div>

          {/* User Info */}
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  {trans.firstName || "First Name"}
                </label>
                <div className="p-3 bg-foreground/30 rounded-lg text-white">
                  {userInfo?.first_name || userInfo?.full_name?.split(" ")[0] || trans.notSet || "Not set"}
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  {trans.lastName || "Last Name"}
                </label>
                <div className="p-3 bg-foreground/30 rounded-lg text-white">
                  {userInfo?.last_name || userInfo?.full_name?.split(" ").slice(1).join(" ") || trans.notSet || "Not set"}
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
                  <HiOutlineMail className="text-lg" />
                  {trans.email || "Email"}
                </label>
                <div className="p-3 bg-foreground/30 rounded-lg flex items-center justify-between">
                  <span className="text-white">{userInfo?.email || trans.notSet || "Not set"}</span>
                 
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
                  <HiOutlineDevicePhoneMobile className="text-lg" />
                  {trans.phone || "Phone Number"}
                </label>
                <div className="p-3 bg-foreground/30 rounded-lg flex items-center justify-between">
                  <span className="text-white">{userInfo?.phone_number || trans.notSet || "Not set"}</span>
                
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Account Actions */}
        <div className="bg-foreground/50 backdrop-blur-sm rounded-xl shadow-lg border border-muted/10 p-6">
          <h2 className="text-2xl font-bold text-white mb-6">
            {trans.accountActions || "Account Actions"}
          </h2>

          <div className="space-y-4">
            <button
              onClick={() => setShowChangePasswordDialog(true)}
              className="w-full flex items-center gap-4 p-4 border border-muted/10 rounded-lg hover:bg-primary/10 hover:border-primary/30 transition-all text-left group bg-foreground/30"
            >
              <div className="p-3 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                <HiOutlineKey className="text-2xl text-primary" />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-white">
                  {trans.changePassword || "Change Password"}
                </div>
                <div className="text-sm text-gray-400">
                  {trans.changePasswordDesc || "Update your account password"}
                </div>
              </div>
            </button>

            <button
              onClick={() => setShowLogoutDialog(true)}
              className="w-full flex items-center gap-4 p-4 border border-muted/10 rounded-lg hover:bg-primary/10 hover:border-primary/30 transition-all text-left group bg-foreground/30"
            >
              <div className="p-3 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                <HiOutlineArrowLeftStartOnRectangle className="text-2xl text-primary" />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-white">
                  {trans.logout || "Logout"}
                </div>
                <div className="text-sm text-gray-400">
                  {trans.logoutDesc || "Sign out of your account"}
                </div>
              </div>
            </button>

            <button
              onClick={() => setShowDeleteDialog(true)}
              className="w-full flex items-center gap-4 p-4 border border-red-500/30 rounded-lg hover:bg-red-500/10 hover:border-red-500/50 transition-all text-left group bg-foreground/30"
            >
              <div className="p-3 rounded-lg bg-red-500/10 group-hover:bg-red-500/20 transition-colors">
                <HiOutlineTrash className="text-2xl text-red-400" />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-red-400">
                  {trans.deleteAccount || "Delete Account"}
                </div>
                <div className="text-sm text-gray-400">
                  {trans.deleteAccountDesc || "Permanently delete your account"}
                </div>
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Change Password Dialog */}
      <GlobalModal
        isOpen={showChangePasswordDialog}
        onClose={() => setShowChangePasswordDialog(false)}
      >
        <div className="bg-foreground p-6 rounded-xl space-y-6 max-w-md w-full">
          <div className="flex items-center gap-4 pb-4 border-b border-muted/20">
            <div className="p-3 rounded-full bg-primary/10">
              <HiOutlineKey className="text-2xl text-primary" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">
                {changePasswordTrans?.title || trans.changePassword || "Change Password"}
              </h2>
              <p className="text-sm mt-1 text-gray-300">
                {changePasswordTrans?.desc || "Enter your current password and new password"}
              </p>
            </div>
          </div>
          {changePasswordTrans && (
            <ChangePasswordForm
              locale={locale}
              trans={changePasswordTrans}
              onSuccess={() => {
                setShowChangePasswordDialog(false);
                toast.success(trans.passwordChangedSuccess || "Password changed successfully");
              }}
            />
          )}
        </div>
      </GlobalModal>

      {/* Change Email Dialog */}
      <GlobalModal
        isOpen={showChangeEmailDialog}
        onClose={() => setShowChangeEmailDialog(false)}
      >
        <div className="bg-foreground p-6 rounded-xl space-y-6 max-w-md w-full">
          <div className="flex items-center gap-4 pb-4 border-b border-muted/20">
            <div className="p-3 rounded-full bg-primary/10">
              <HiOutlineMail className="text-2xl text-primary" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">
                {changeEmailTrans?.title || trans.changeEmail || "Change Email"}
              </h2>
              <p className="text-sm mt-1 text-gray-300">
                {changeEmailTrans?.desc || "Enter your new email address"}
              </p>
            </div>
          </div>
          <ChangeEmailForm
            locale={locale}
            trans={changeEmailTrans}
            currentEmail={userInfo?.email}
            onSuccess={() => {
              setShowChangeEmailDialog(false);
              toast.success(trans.emailChangedSuccess || "Email changed successfully");
              // Refresh user info
              window.location.reload();
            }}
          />
        </div>
      </GlobalModal>

      {/* Change Phone Dialog */}
      <GlobalModal
        isOpen={showChangePhoneDialog}
        onClose={() => setShowChangePhoneDialog(false)}
      >
        <div className="bg-foreground p-6 rounded-xl space-y-6 max-w-md w-full">
          <div className="flex items-center gap-4 pb-4 border-b border-muted/20">
            <div className="p-3 rounded-full bg-primary/10">
              <HiOutlineDevicePhoneMobile className="text-2xl text-primary" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">
                {changePhoneTrans?.title || trans.changePhone || "Change Phone Number"}
              </h2>
              <p className="text-sm mt-1 text-gray-300">
                {changePhoneTrans?.desc || "Enter your new phone number"}
              </p>
            </div>
          </div>
          <ChangePhoneForm
            locale={locale}
            trans={changePhoneTrans}
            currentPhone={userInfo?.phone_number}
            onSuccess={() => {
              setShowChangePhoneDialog(false);
              toast.success(trans.phoneChangedSuccess || "Phone number changed successfully");
              // Refresh user info
              window.location.reload();
            }}
          />
        </div>
      </GlobalModal>

      {/* Logout Confirmation Dialog */}
      <GlobalModal
        isOpen={showLogoutDialog}
        onClose={() => setShowLogoutDialog(false)}
      >
        <div className="bg-foreground p-6 rounded-xl space-y-6 max-w-md w-full">
          <div className="flex items-center gap-4 pb-4 border-b border-muted/20">
            <div className="p-3 rounded-full bg-primary/10">
              <HiOutlineArrowLeftStartOnRectangle className="text-2xl text-primary" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">
                {trans.logoutConfirmTitle || "Confirm Logout"}
              </h2>
              <p className="text-sm mt-1 text-gray-300">
                {trans.logoutConfirmMessage || "Are you sure you want to logout?"}
              </p>
            </div>
          </div>
          <div className="flex gap-3 justify-end pt-4 border-t border-muted/20">
            <Button variant="ghost" onClick={() => setShowLogoutDialog(false)}>
              {trans.cancel || "Cancel"}
            </Button>
            <Button
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="bg-primary hover:bg-primary/90 text-black font-semibold"
            >
              {isLoggingOut ? trans.loggingOut || "Logging out..." : trans.confirm || "Confirm"}
            </Button>
          </div>
        </div>
      </GlobalModal>

      {/* Delete Account Confirmation Dialog */}
      <GlobalModal
        isOpen={showDeleteDialog}
        onClose={() => {
          setShowDeleteDialog(false);
          setPassword("");
          setShowPassword(false);
        }}
      >
        <div className="bg-foreground p-6 rounded-xl space-y-6 max-w-md w-full border-2 border-red-500/20">
          <div className="flex items-center gap-4 pb-4 border-b border-red-500/20">
            <div className="p-3 rounded-full bg-red-500/10">
              <HiOutlineTrash className="text-2xl text-red-400" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-red-400">
                {trans.deleteAccountConfirmTitle || "Delete Account"}
              </h2>
              <p className="text-sm mt-1 text-gray-300">
                {trans.deleteAccountConfirmMessage || "This action cannot be undone"}
              </p>
            </div>
          </div>
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-sm text-red-300 flex items-center gap-2">
              <span className="text-lg">⚠️</span>
              <span>
                {trans.deleteWarning || "This action is permanent and cannot be undone. All your data will be permanently deleted."}
              </span>
            </p>
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-white">
              {trans.passwordLabel || "Password"} <span className="text-red-400">*</span>
            </label>
            <div className="flex items-center w-full p-3 border-2 border-muted/20 bg-foreground/50 rounded-lg focus-within:border-red-500/50 transition-colors">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={trans.passwordPlaceholder || "Enter your password"}
                className="w-full focus:outline-none bg-transparent text-white placeholder:text-gray-400"
              />
              <span
                className="text-lg cursor-pointer hover:text-red-400 transition-colors ml-2 text-gray-300"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <BsEyeSlashFill /> : <BsEyeFill />}
              </span>
            </div>
          </div>
          <div className="flex gap-3 justify-end pt-4 border-t border-red-500/20">
            <Button
              variant="ghost"
              onClick={() => {
                setShowDeleteDialog(false);
                setPassword("");
                setShowPassword(false);
              }}
              disabled={isDeleting}
            >
              {trans.cancel || "Cancel"}
            </Button>
            <Button
              onClick={handleDeleteAccount}
              disabled={isDeleting || !password.trim()}
              className="bg-red-500 hover:bg-red-600 text-white font-semibold"
            >
              {isDeleting ? trans.deleting || "Deleting..." : trans.confirm || "Confirm"}
            </Button>
          </div>
        </div>
      </GlobalModal>
    </>
  );
}

