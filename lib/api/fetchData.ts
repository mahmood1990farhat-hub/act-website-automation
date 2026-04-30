
import { extract_error } from "./errorApi";

type FetchOptions = {
  endpoint: string;
  token?: string;
  queryParams?: Record<string, string>;
};

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function fetchData<T>({
  endpoint,
  token,
  queryParams,
}: FetchOptions): Promise<T> {
  try {
    const url = `${BASE_URL}${endpoint}`;

    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const queryString = queryParams
      ? "?" + new URLSearchParams(queryParams).toString()
      : "";

    const finalUrl = `${url}${queryString}`;

    const response = await fetch(finalUrl, {
      method: "GET",
      headers,
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
      // const err = await response.json();
      // toast.error(extract_error(err));
      throw new Error(
        `Failed to fetch data from ${finalUrl}. Status: ${response.status}`
      );
    }

    const data: T = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching data:", error);
    throw error;
  }
}
