import { toast } from "react-toastify";
import { extract_error } from "./errorApi";

type PostOptions = {
  endpoint: string;
  token?: string;
  body?: Record<string, any>;
  queryParams?: Record<string, string>;
  noToast?: boolean;
};

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function postData<T>({
  endpoint,
  token,
  body,
  queryParams,
  noToast = false, // Default to false to show toasts automatically
}: PostOptions): Promise<T> {
  try {
    const url = `${BASE_URL}${endpoint}`;

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const queryString = queryParams
      ? "?" + new URLSearchParams(queryParams).toString()
      : "";

    const finalUrl = `${url}${queryString}`;

    const response = await fetch(finalUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(body || {}),
    });

    if (!response.ok) {
      // Handle 401 Unauthorized - token expired
      if (response.status === 401) {
        // Check if we're in admin dashboard context
        if (typeof window !== "undefined") {
          const pathname = window.location.pathname;
          if (pathname.includes("/dashboard")) {
            // Get locale from pathname
            const locale = pathname.split("/")[1] || "en";
            // Clear cookies and redirect to admin login
            document.cookie = "userToken=; path=/; max-age=0";
            document.cookie = "account_type=; path=/; max-age=0";
            document.cookie = "user_id=; path=/; max-age=0";
            window.location.href = `/${locale}/admin/login`;
            throw new Error("Token expired - redirecting to login");
          }
        }
      }
      const err = await response.json();
      // Only show error toast if noToast is false (explicitly requested)
      if (!noToast) {
        toast.error(extract_error(err));
      }
      throw new Error(
        `Failed to post data to ${finalUrl}. Status: ${response.status}`
      );
    }

    const data: T | any = await response.json();
    // Only show success toast if noToast is false (explicitly requested)
    if (!noToast) {
      toast.success(data.message);
    }
    return data;
  } catch (error) {
    console.error("Error posting data:", error);
    throw error;
  }
}
