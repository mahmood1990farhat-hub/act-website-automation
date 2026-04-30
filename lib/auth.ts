import { cookies } from "next/headers";

export type AccountType = "normal" | "normal_driver" | "passenger";

export interface AuthUser {
  id: string;
  accountType: AccountType;
  isAdminVerified: boolean;
  onboardingStatus?: {
    status: string;
    next_step: string;
    can_upload_documents: boolean;
  };
}

export async function getAuthUser(): Promise<AuthUser | null> {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get("userToken")?.value;
    
    if (!token) {
      return null;
    }

    const accountType = cookieStore.get("account_type")?.value as AccountType;
    const isAdminVerified = cookieStore.get("is_admin_verified")?.value === "true";
    const userId = cookieStore.get("user_id")?.value;

    if (!accountType || !userId) {
      return null;
    }

    return {
      id: userId,
      accountType,
      isAdminVerified,
    };
  } catch (error) {
    console.error("Error getting auth user:", error);
    return null;
  }
}

export function canAccessRoute(user: AuthUser | null, route: string): boolean {
  if (!user) {
    // No user - can only access public routes
    return route.startsWith("/") && !route.includes("/dashboard") && !route.includes("/driver");
  }

  switch (user.accountType) {
    case "normal":
      // Admin - can access dashboard
      return route.includes("/dashboard");
    
    case "normal_driver":
      // Driver - check verification status
      if (user.isAdminVerified) {
        // Verified driver - can access driver routes
        return route.includes("/driver") && !route.includes("/upload-documents");
      } else {
        // Unverified driver - can only access upload documents or public routes
        return route.includes("/driver/upload-documents") || (!route.includes("/dashboard") && !route.includes("/driver"));
      }
    
    case "passenger":
      // Passenger - can access public routes only
      return !route.includes("/dashboard") && !route.includes("/driver");
    
    default:
      return false;
  }
}

export function getRedirectPath(user: AuthUser | null): string {
  if (!user) {
    return "/";
  }

  switch (user.accountType) {
    case "normal":
      return "/dashboard";
    
    case "normal_driver":
      if (user.isAdminVerified) {
        return "/driver";
      } else {
        // Check onboarding status for unverified drivers
        if (user.onboardingStatus?.can_upload_documents) {
          return "/driver/upload-documents";
        } else {
          return "/"; // Show as guest until verified
        }
      }
    
    case "passenger":
      return "/";
    
    default:
      return "/";
  }
}

