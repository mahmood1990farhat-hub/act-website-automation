"use client";

import React, { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, SubmitHandler } from "react-hook-form";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { Locale } from "../../../../i18n.config";
import { fetchData } from "@/lib/api/fetchData";
import { postData } from "@/lib/api/postData";
import { toast } from "react-toastify";
import { Button } from "@/components/ui/button";
import IsLoading from "../ISloading";
import GlobalModal from "../GlobalModal";
import { extract_error } from "@/lib/api/errorApi";
import { FaCheckCircle, FaTimesCircle, FaFilter, FaDownload } from "react-icons/fa";
import Pagination from "../Pagination";

// Types
type DriverEarning = {
  driver_id: number;
  driver_name: string;
  driver_email: string;
  driver_phone: string;
  currency: string;
  total_gross: number;
  total_commission: number;
  total_net: number;
  total_earnings_count: number;
  available_for_payout: number;
  pending: number;
  locked: number;
  processing: number;
  paid: number;
};

type DriversEarningsResponse = {
  success: boolean;
  data: {
    drivers: DriverEarning[];
    totals: {
      total_gross: number;
      total_commission: number;
      total_net: number;
      total_earnings_count: number;
      available_for_payout: number;
      pending: number;
      locked: number;
      processing: number;
      paid: number;
    };
  };
};

type Earning = {
  id: number;
  driver: {
    id: number;
    name: string;
    email: string;
    phone: string;
  };
  trip: {
    id: number;
    cost: number;
    status: string;
    trip_date: string;
    car_type: string;
  } | null;
  gross_amount: number;
  commission_amount: number;
  net_amount: number;
  currency: string;
  status: "AVAILABLE" | "PENDING" | "LOCKED" | "PROCESSING" | "PAID";
  stripe_transfer_id: string | null;
  payout_batch_id: string | null;
  created_at: string;
  paid_at: string | null;
};

type EarningsReportingResponse = {
  success: boolean;
  data: {
    earnings: Earning[];
    summary: {
      total_gross: number;
      total_commission: number;
      total_net: number;
      total_count: number;
      available: number;
      pending: number;
      locked: number;
      processing: number;
      paid: number;
    };
    pagination: {
      page: number;
      page_size: number;
      total_count: number;
      total_pages: number;
      has_next: boolean;
      has_previous: boolean;
    };
  };
};

type WithdrawalRequest = {
  id: string;
  driver: {
    id: number;
    name: string;
    email: string;
    phone: string;
  };
  status: "SUBMITTED" | "APPROVED" | "REJECTED" | "PROCESSING" | "COMPLETED";
  requested_amount: number | null;
  currency: string;
  note: string;
  reviewed_by: {
    id: number;
    email: string;
  } | null;
  reviewed_at: string | null;
  admin_note: string;
  payout_batch_id: string | null;
  created_at: string;
  updated_at: string;
  current_available_balance: number;
};

type WithdrawalRequestsResponse = {
  success: boolean;
  data: {
    requests: WithdrawalRequest[];
    pagination: {
      page: number;
      page_size: number;
      total_count: number;
      total_pages: number;
      has_next: boolean;
      has_previous: boolean;
    };
  };
};

type ApproveWithdrawalResponse = {
  success: boolean;
  message: string;
  data: {
    request_id: string;
    status: string;
    reviewed_at: string;
  };
};

type BulkPayoutResponse = {
  success: boolean;
  data: {
    batch_id: string;
    status: string;
    mode: string;
    total_earnings: number;
    successful: number;
    failed: number;
    results: Array<{
      driver_id: number;
      earning_id: number;
      status: string;
      reason?: string;
    }>;
  };
};

type EarningsProps = {
  trans: any;
  token?: string;
  locale: Locale;
};

type ApproveFormData = {
  admin_note: string;
};

type BulkPayoutFormData = {
  mode: "approved_requests";
  request_ids?: string[];
  driver_id?: number;
};

export default function Earnings({
  trans,
  token,
  locale,
}: EarningsProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  
  // Get tab from URL or default to "drivers"
  const tabFromUrl = searchParams.get("tab") as "drivers" | "reporting" | "withdrawals" | null;
  const validTabs: ("drivers" | "reporting" | "withdrawals")[] = ["drivers", "reporting", "withdrawals"];
  const initialTab = tabFromUrl && validTabs.includes(tabFromUrl) ? tabFromUrl : "drivers";
  
  const [activeTab, setActiveTab] = useState<"drivers" | "reporting" | "withdrawals">(initialTab);
  const [reportingPage, setReportingPage] = useState(1);
  const [withdrawalPage, setWithdrawalPage] = useState(1);
  const [selectedRequest, setSelectedRequest] = useState<WithdrawalRequest | null>(null);
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showBulkPayoutModal, setShowBulkPayoutModal] = useState(false);
  const [selectedRequestIds, setSelectedRequestIds] = useState<string[]>([]);
  const [withdrawalFilters, setWithdrawalFilters] = useState({
    driver_id: "",
    status: "",
  });

  const queryClient = useQueryClient();
  const isUpdatingFromUrl = useRef(false);
  const lastUrlTab = useRef<string | null>(null);

  // Get current tab from URL as a stable string
  const currentUrlTab = searchParams.get("tab");

  // Update activeTab when URL changes (e.g., browser back/forward)
  useEffect(() => {
    // Only run if URL tab actually changed
    if (currentUrlTab === lastUrlTab.current) {
      return;
    }
    
    lastUrlTab.current = currentUrlTab;
    const tabFromUrl = currentUrlTab as "drivers" | "reporting" | "withdrawals" | null;
    const normalizedTabFromUrl = tabFromUrl && validTabs.includes(tabFromUrl) ? tabFromUrl : "drivers";
    
    // Only update if different from current activeTab
    if (normalizedTabFromUrl !== activeTab) {
      isUpdatingFromUrl.current = true;
      setActiveTab(normalizedTabFromUrl);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUrlTab]);

  // Sync tab with URL when user changes tab (not when updating from URL)
  useEffect(() => {
    if (isUpdatingFromUrl.current) {
      isUpdatingFromUrl.current = false;
      return;
    }

    // Check if URL already matches activeTab
    const urlTab = searchParams.get("tab") as "drivers" | "reporting" | "withdrawals" | null;
    const normalizedUrlTab = urlTab && validTabs.includes(urlTab) ? urlTab : "drivers";
    
    // Only update URL if activeTab doesn't match URL
    if (normalizedUrlTab !== activeTab) {
      const params = new URLSearchParams(searchParams.toString());
      if (activeTab === "drivers") {
        params.delete("tab");
      } else {
        params.set("tab", activeTab);
      }
      const queryString = params.toString();
      const newUrl = queryString ? `${pathname}?${queryString}` : pathname;
      lastUrlTab.current = activeTab === "drivers" ? null : activeTab;
      router.push(newUrl, { scroll: false });
    }
  }, [activeTab, router, searchParams, pathname, validTabs]);

  // Fetch drivers earnings
  const { data: driversEarningsData, isLoading: driversLoading } = useQuery<DriversEarningsResponse>({
    queryKey: ["drivers-earnings", token],
    queryFn: () =>
      fetchData({
        endpoint: "/api/admin-panel/earnings/drivers/",
        token,
      }),
    enabled: !!token && activeTab === "drivers",
    retry: 1,
    refetchOnWindowFocus: false,
  });

  // Fetch earnings reporting
  const { data: earningsReportingData, isLoading: reportingLoading } = useQuery<EarningsReportingResponse>({
    queryKey: ["earnings-reporting", reportingPage, token],
    queryFn: () =>
      fetchData({
        endpoint: "/api/admin-panel/earnings/reporting/",
        token,
        queryParams: {
          page: reportingPage.toString(),
          page_size: "20",
        },
      }),
    enabled: !!token && activeTab === "reporting",
    retry: 1,
    refetchOnWindowFocus: false,
  });

  // Fetch withdrawal requests
  const { data: withdrawalRequestsData, isLoading: withdrawalsLoading } = useQuery<WithdrawalRequestsResponse>({
    queryKey: ["withdrawal-requests", withdrawalPage, withdrawalFilters, token],
    queryFn: () => {
      const params: Record<string, string> = {
        page: withdrawalPage.toString(),
        page_size: "10",
      };
      if (withdrawalFilters.driver_id) params.driver_id = withdrawalFilters.driver_id;
      if (withdrawalFilters.status) params.status = withdrawalFilters.status;
      return fetchData({
        endpoint: "/api/admin-panel/withdrawal-requests/",
        token,
        queryParams: params,
      });
    },
    enabled: !!token && activeTab === "withdrawals",
    retry: 1,
    refetchOnWindowFocus: false,
  });

  // Approve withdrawal mutation
  const approveMutation = useMutation({
    mutationFn: (data: ApproveFormData) =>
      postData<ApproveWithdrawalResponse>({
        endpoint: `/api/admin-panel/withdrawal-requests/${selectedRequest?.id}/approve/`,
        token,
        body: data,
        noToast: false, // Let API show toast
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["withdrawal-requests"] });
      queryClient.invalidateQueries({ queryKey: ["drivers-earnings"] });
      setShowApproveModal(false);
      setSelectedRequest(null);
    },
    onError: () => {
      // Error toast is handled by postData
    },
  });

  // Bulk payout mutation
  const bulkPayoutMutation = useMutation({
    mutationFn: (data: BulkPayoutFormData) =>
      postData<BulkPayoutResponse>({
        endpoint: "/api/admin-panel/payouts/run/",
        token,
        body: data,
        noToast: false, // Let API show toast
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["withdrawal-requests"] });
      queryClient.invalidateQueries({ queryKey: ["drivers-earnings"] });
      queryClient.invalidateQueries({ queryKey: ["earnings-reporting"] });
      setShowBulkPayoutModal(false);
      setSelectedRequestIds([]);
    },
    onError: () => {
      // Error toast is handled by postData
    },
  });

  const { register: approveRegister, handleSubmit: approveHandleSubmit, reset: approveReset } = useForm<ApproveFormData>({
    defaultValues: {
      admin_note: "",
    },
  });

  const { register: bulkRegister, handleSubmit: bulkHandleSubmit, reset: bulkReset } = useForm<BulkPayoutFormData>({
    defaultValues: {
      mode: "approved_requests",
      request_ids: [],
      driver_id: undefined,
    },
  });

  const handleApprove = (request: WithdrawalRequest) => {
    setSelectedRequest(request);
    setShowApproveModal(true);
    approveReset({ admin_note: "" });
  };

  const handleBulkPayout = () => {
    if (selectedRequestIds.length === 0) {
      toast.error(trans.earnings?.selectRequests || "Please select at least one request");
      return;
    }
    bulkReset({ mode: "approved_requests", request_ids: selectedRequestIds, driver_id: undefined });
    setShowBulkPayoutModal(true);
  };

  const onApproveSubmit: SubmitHandler<ApproveFormData> = (data) => {
    if (selectedRequest) {
      approveMutation.mutate(data);
    }
  };

  const onBulkPayoutSubmit: SubmitHandler<BulkPayoutFormData> = (data) => {
    const payload: any = {
      mode: "approved_requests",
    };
    
    // Only include request_ids if there are selected requests
    if (selectedRequestIds.length > 0) {
      payload.request_ids = selectedRequestIds;
    }
    
    // Only include driver_id if provided
    if (data.driver_id && data.driver_id > 0) {
      payload.driver_id = Number(data.driver_id);
    }
    
    bulkPayoutMutation.mutate(payload);
  };

  const toggleRequestSelection = (requestId: string) => {
    setSelectedRequestIds((prev) =>
      prev.includes(requestId)
        ? prev.filter((id) => id !== requestId)
        : [...prev, requestId]
    );
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "AVAILABLE":
      case "APPROVED":
      case "COMPLETED":
        return "bg-green-50 text-green-700 border-green-200";
      case "PENDING":
      case "SUBMITTED":
        return "bg-yellow-50 text-yellow-700 border-yellow-200";
      case "LOCKED":
      case "PROCESSING":
        return "bg-blue-50 text-blue-700 border-blue-200";
      case "PAID":
        return "bg-purple-50 text-purple-700 border-purple-200";
      case "REJECTED":
        return "bg-red-50 text-red-700 border-red-200";
      default:
        return "bg-gray-50 text-gray-700 border-gray-200";
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-GB", {
      style: "currency",
      currency: "GBP",
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(locale === "ar" ? "ar-SA" : "en-GB", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Tabs */}
      <div className="flex flex-wrap gap-1 md:gap-2 border-b-2 border-border overflow-x-auto">
        <button
          onClick={() => setActiveTab("drivers")}
          className={`px-2 md:px-4 py-2 text-xs md:text-base font-semibold transition-colors whitespace-nowrap ${
            activeTab === "drivers"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {trans.earnings?.driversTab || "Drivers Earnings"}
        </button>
        <button
          onClick={() => setActiveTab("reporting")}
          className={`px-2 md:px-4 py-2 text-xs md:text-base font-semibold transition-colors whitespace-nowrap ${
            activeTab === "reporting"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {trans.earnings?.reportingTab || "Earnings Reporting"}
        </button>
        <button
          onClick={() => setActiveTab("withdrawals")}
          className={`px-2 md:px-4 py-2 text-xs md:text-base font-semibold transition-colors whitespace-nowrap ${
            activeTab === "withdrawals"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {trans.earnings?.withdrawalsTab || "Withdrawal Requests"}
        </button>
      </div>

      {/* Drivers Earnings Tab */}
      {activeTab === "drivers" && (
        <div>
          {driversLoading ? (
            <div className="flex justify-center items-center min-h-[400px]">
              <IsLoading />
            </div>
          ) : driversEarningsData?.data ? (
            <div className="space-y-4 md:space-y-6">
              {/* Description */}
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 md:p-4">
                <p className="text-xs md:text-sm text-blue-800 dark:text-blue-200">
                  <strong>{trans.earnings?.driversTabDescription || "Drivers Summary:"}</strong> {trans.earnings?.driversTabDescriptionText || "This view shows aggregated earnings totals for each driver, including their total gross, commission, net earnings, and available balance for payout."}
                </p>
              </div>
              
              {/* Totals Summary */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
                <div className="bg-card rounded-xl shadow-lg border-2 border-border p-3 md:p-4">
                  <p className="text-xs md:text-sm text-muted-foreground mb-1">
                    {trans.earnings?.totalGross || "Total Gross"}
                  </p>
                  <p className="text-lg md:text-2xl font-bold text-foreground break-words">
                    {formatCurrency(driversEarningsData.data.totals.total_gross)}
                  </p>
                </div>
                <div className="bg-card rounded-xl shadow-lg border-2 border-border p-3 md:p-4">
                  <p className="text-xs md:text-sm text-muted-foreground mb-1">
                    {trans.earnings?.totalCommission || "Total Commission"}
                  </p>
                  <p className="text-lg md:text-2xl font-bold text-foreground break-words">
                    {formatCurrency(driversEarningsData.data.totals.total_commission)}
                  </p>
                </div>
                <div className="bg-card rounded-xl shadow-lg border-2 border-border p-3 md:p-4">
                  <p className="text-xs md:text-sm text-muted-foreground mb-1">
                    {trans.earnings?.totalNet || "Total Net"}
                  </p>
                  <p className="text-lg md:text-2xl font-bold text-foreground break-words">
                    {formatCurrency(driversEarningsData.data.totals.total_net)}
                  </p>
                </div>
                <div className="bg-card rounded-xl shadow-lg border-2 border-border p-3 md:p-4">
                  <p className="text-xs md:text-sm text-muted-foreground mb-1">
                    {trans.earnings?.availableForPayout || "Available for Payout"}
                  </p>
                  <p className="text-lg md:text-2xl font-bold text-green-600 break-words">
                    {formatCurrency(driversEarningsData.data.totals.available_for_payout)}
                  </p>
                </div>
                <div className="bg-card rounded-xl shadow-lg border-2 border-border p-3 md:p-4">
                  <p className="text-xs md:text-sm text-muted-foreground mb-1">
                    {trans.earnings?.pending || "Pending"}
                  </p>
                  <p className="text-lg md:text-2xl font-bold text-yellow-600 break-words">
                    {formatCurrency(driversEarningsData.data.totals.pending)}
                  </p>
                </div>
                <div className="bg-card rounded-xl shadow-lg border-2 border-border p-3 md:p-4">
                  <p className="text-xs md:text-sm text-muted-foreground mb-1">
                    {trans.earnings?.paid || "Paid"}
                  </p>
                  <p className="text-lg md:text-2xl font-bold text-purple-600 break-words">
                    {formatCurrency(driversEarningsData.data.totals.paid)}
                  </p>
                </div>
              </div>

              {/* Drivers List */}
              {driversEarningsData.data.drivers.length > 0 ? (
                <>
                  {/* Mobile Card View */}
                  <div className="block md:hidden space-y-3">
                    {driversEarningsData.data.drivers.map((driver) => (
                      <div key={driver.driver_id} className="bg-card rounded-xl shadow-lg border-2 border-border p-4 space-y-2">
                        <div className="flex justify-between items-start">
                          <p className="font-semibold text-sm">{driver.driver_name}</p>
                          <span className="text-xs text-muted-foreground">#{driver.driver_id}</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.email || "Email"}</p>
                            <p className="font-semibold break-words">{driver.driver_email}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.phone || "Phone"}</p>
                            <p className="font-semibold">{driver.driver_phone}</p>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-border">
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.totalGross || "Gross"}</p>
                            <p className="font-semibold">{formatCurrency(driver.total_gross)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.commission || "Commission"}</p>
                            <p className="font-semibold">{formatCurrency(driver.total_commission)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.net || "Net"}</p>
                            <p className="font-semibold">{formatCurrency(driver.total_net)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.available || "Available"}</p>
                            <p className="font-semibold text-green-600">{formatCurrency(driver.available_for_payout)}</p>
                          </div>
                        </div>
                        <div className="pt-2 border-t border-border">
                          <p className="text-xs text-muted-foreground">{trans.earnings?.earningsCount || "Earnings Count"}: <span className="font-semibold text-foreground">{driver.total_earnings_count}</span></p>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  {/* Desktop Table View */}
                  <div className="hidden md:block bg-card rounded-xl shadow-xl border-2 border-border overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b-2 border-border bg-gray-100 dark:bg-gray-800">
                          <th className="text-start py-4 px-4 font-bold">{trans.earnings?.driverName || "Driver"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.email || "Email"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.phone || "Phone"}</th>
                          <th className="text-start py-4 px-4 font-bold">{trans.earnings?.totalGross || "Gross"}</th>
                          <th className="text-start py-4 px-4 font-bold">{trans.earnings?.commission || "Commission"}</th>
                          <th className="text-start py-4 px-4 font-bold">{trans.earnings?.net || "Net"}</th>
                          <th className="text-start py-4 px-4 font-bold">{trans.earnings?.available || "Available"}</th>
                          <th className="text-start py-4 px-4 font-bold">{trans.earnings?.earningsCount || "Count"}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {driversEarningsData.data.drivers.map((driver) => (
                          <tr key={driver.driver_id} className="border-b border-border hover:bg-muted">
                            <td className="py-3 px-4 font-semibold">{driver.driver_name}</td>
                              <td className="py-3 px-4 text-sm break-words">{driver.driver_email}</td>
                              <td className="py-3 px-4 text-sm">{driver.driver_phone}</td>
                            <td className="py-3 px-4">{formatCurrency(driver.total_gross)}</td>
                            <td className="py-3 px-4">{formatCurrency(driver.total_commission)}</td>
                            <td className="py-3 px-4 font-semibold">{formatCurrency(driver.total_net)}</td>
                            <td className="py-3 px-4 text-green-600 font-semibold">
                              {formatCurrency(driver.available_for_payout)}
                            </td>
                              <td className="py-3 px-4">{driver.total_earnings_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
                </>
              ) : (
                <div className="bg-card rounded-xl shadow-xl border-2 border-border p-8 text-center">
                  <p className="text-muted-foreground">{trans.earnings?.noDrivers || "No drivers found"}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-card rounded-xl shadow-xl border-2 border-border p-8 text-center">
              <p className="text-red-600">{trans.earnings?.loadError || "Failed to load drivers earnings"}</p>
            </div>
          )}
        </div>
      )}

      {/* Earnings Reporting Tab */}
      {activeTab === "reporting" && (
        <div>
          {reportingLoading ? (
            <div className="flex justify-center items-center min-h-[400px]">
              <IsLoading />
            </div>
          ) : earningsReportingData?.data ? (
            <div className="space-y-4 md:space-y-6">
              {/* Description */}
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3 md:p-4">
                <p className="text-xs md:text-sm text-green-800 dark:text-green-200">
                  <strong>{trans.earnings?.reportingTabDescription || "Individual Earnings Records:"}</strong> {trans.earnings?.reportingTabDescriptionText || "This view shows detailed individual earnings records with trip information, including trip date, cost, car type, and trip status for each earning entry."}
                </p>
              </div>
              
              {/* Summary Cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
                <div className="bg-card rounded-xl shadow-lg border-2 border-border p-3 md:p-4">
                  <p className="text-xs md:text-sm text-muted-foreground mb-1">{trans.earnings?.totalGross || "Total Gross"}</p>
                  <p className="text-base md:text-xl font-bold break-words">{formatCurrency(earningsReportingData.data.summary.total_gross)}</p>
                </div>
                <div className="bg-card rounded-xl shadow-lg border-2 border-border p-3 md:p-4">
                  <p className="text-xs md:text-sm text-muted-foreground mb-1">{trans.earnings?.totalNet || "Total Net"}</p>
                  <p className="text-base md:text-xl font-bold break-words">{formatCurrency(earningsReportingData.data.summary.total_net)}</p>
                </div>
                <div className="bg-card rounded-xl shadow-lg border-2 border-border p-3 md:p-4">
                  <p className="text-xs md:text-sm text-muted-foreground mb-1">{trans.earnings?.totalCount || "Total Count"}</p>
                  <p className="text-base md:text-xl font-bold">{earningsReportingData.data.summary.total_count}</p>
                </div>
                <div className="bg-card rounded-xl shadow-lg border-2 border-border p-3 md:p-4">
                  <p className="text-xs md:text-sm text-muted-foreground mb-1">{trans.earnings?.available || "Available"}</p>
                  <p className="text-base md:text-xl font-bold text-green-600 break-words">
                    {formatCurrency(earningsReportingData.data.summary.available)}
                  </p>
                </div>
              </div>

              {/* Earnings Table */}
              {earningsReportingData.data.earnings.length > 0 ? (
                <>
                  {/* Mobile Card View */}
                  <div className="block md:hidden space-y-3">
                    {earningsReportingData.data.earnings.map((earning) => (
                      <div key={earning.id} className="bg-card rounded-xl shadow-lg border-2 border-border p-4 space-y-2">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-semibold text-sm">{earning.driver.name}</p>
                            <p className="text-xs text-muted-foreground">{earning.driver.email}</p>
                          </div>
                          <span className="text-xs text-muted-foreground">#{earning.id}</span>
                        </div>
                        {earning.trip && (
                          <div className="bg-muted/50 rounded-lg p-2 text-xs">
                            <p className="font-semibold mb-1">{trans.earnings?.tripInfo || "Trip Info"}</p>
                            <div className="grid grid-cols-2 gap-2">
                              <div>
                                <p className="text-muted-foreground">{trans.earnings?.tripDate || "Trip Date"}</p>
                                <p className="font-semibold">{new Date(earning.trip.trip_date).toLocaleDateString()}</p>
                              </div>
                              <div>
                                <p className="text-muted-foreground">{trans.earnings?.tripCost || "Trip Cost"}</p>
                                <p className="font-semibold">{formatCurrency(earning.trip.cost)}</p>
                              </div>
                              <div>
                                <p className="text-muted-foreground">{trans.earnings?.carType || "Car Type"}</p>
                                <p className="font-semibold">{earning.trip.car_type}</p>
                              </div>
                              <div>
                                <p className="text-muted-foreground">{trans.earnings?.tripStatus || "Trip Status"}</p>
                                <p className="font-semibold capitalize">{earning.trip.status}</p>
                              </div>
                            </div>
                          </div>
                        )}
                        <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-border">
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.gross || "Gross"}</p>
                            <p className="font-semibold">{formatCurrency(earning.gross_amount)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.commission || "Commission"}</p>
                            <p className="font-semibold">{formatCurrency(earning.commission_amount)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.net || "Net"}</p>
                            <p className="font-semibold">{formatCurrency(earning.net_amount)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.status || "Status"}</p>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold border ${getStatusColor(earning.status)}`}>
                              {earning.status}
                            </span>
                          </div>
                        </div>
                        <div className="pt-2 border-t border-border">
                          <p className="text-xs text-muted-foreground">{trans.earnings?.createdAt || "Created"}: <span className="font-semibold text-foreground">{formatDate(earning.created_at)}</span></p>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  {/* Desktop Table View */}
                  <div className="hidden md:block bg-card rounded-xl shadow-xl border-2 border-border overflow-hidden">
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b-2 border-border bg-gray-100 dark:bg-gray-800">
                            <th className="text-start py-4 px-4 font-bold">ID</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.driverName || "Driver"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.tripInfo || "Trip"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.gross || "Gross"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.commission || "Commission"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.net || "Net"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.status || "Status"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.createdAt || "Created"}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {earningsReportingData.data.earnings.map((earning) => (
                            <tr key={earning.id} className="border-b border-border hover:bg-muted">
                              <td className="py-3 px-4">#{earning.id}</td>
                              <td className="py-3 px-4">
                                <div>
                                  <p className="font-semibold">{earning.driver.name}</p>
                                  <p className="text-xs text-muted-foreground">{earning.driver.email}</p>
                                </div>
                              </td>
                              <td className="py-3 px-4">
                                {earning.trip ? (
                                  <div className="text-xs">
                                    <p className="font-semibold">#{earning.trip.id}</p>
                                    <p className="text-muted-foreground">{new Date(earning.trip.trip_date).toLocaleDateString()}</p>
                                    <p className="text-muted-foreground">{earning.trip.car_type}</p>
                                  </div>
                                ) : (
                                  <span className="text-muted-foreground text-xs">N/A</span>
                                )}
                              </td>
                              <td className="py-3 px-4">{formatCurrency(earning.gross_amount)}</td>
                              <td className="py-3 px-4">{formatCurrency(earning.commission_amount)}</td>
                              <td className="py-3 px-4 font-semibold">{formatCurrency(earning.net_amount)}</td>
                              <td className="py-3 px-4">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${getStatusColor(earning.status)}`}>
                                  {earning.status}
                                </span>
                              </td>
                              <td className="py-3 px-4 text-xs">{formatDate(earning.created_at)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                  {earningsReportingData.data.pagination.total_pages > 1 && (
                    <div className="flex justify-center">
                      <Pagination
                        currentPage={reportingPage}
                        onPageChange={setReportingPage}
                        locale={locale}
                        totalPages={earningsReportingData.data.pagination.total_pages}
                      />
                    </div>
                  )}
                </>
              ) : (
                <div className="bg-card rounded-xl shadow-xl border-2 border-border p-8 text-center">
                  <p className="text-muted-foreground">{trans.earnings?.noEarnings || "No earnings found"}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-card rounded-xl shadow-xl border-2 border-border p-8 text-center">
              <p className="text-red-600">{trans.earnings?.loadError || "Failed to load earnings reporting"}</p>
            </div>
          )}
        </div>
      )}

      {/* Withdrawal Requests Tab */}
      {activeTab === "withdrawals" && (
        <div>
          {withdrawalsLoading ? (
            <div className="flex justify-center items-center min-h-[400px]">
              <IsLoading />
            </div>
          ) : withdrawalRequestsData?.data ? (
            <div className="space-y-4 md:space-y-6">
              {/* Filters and Actions */}
              <div className="bg-card rounded-xl shadow-lg border-2 border-border p-3 md:p-4">
                <div className="flex flex-col gap-3 md:gap-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                    <div>
                      <label className="block text-xs md:text-sm font-medium mb-2">
                        {trans.earnings?.driverId || "Driver ID"}
                      </label>
                      <input
                        type="number"
                        value={withdrawalFilters.driver_id}
                        onChange={(e) => setWithdrawalFilters({ ...withdrawalFilters, driver_id: e.target.value })}
                        placeholder={trans.earnings?.driverIdPlaceholder || "Filter by driver ID"}
                        className="w-full p-2 md:p-3 text-sm md:text-base border-2 border-border rounded-lg bg-background text-foreground"
                      />
                    </div>
                    <div>
                      <label className="block text-xs md:text-sm font-medium mb-2">
                        {trans.earnings?.status || "Status"}
                      </label>
                      <select
                        value={withdrawalFilters.status}
                        onChange={(e) => setWithdrawalFilters({ ...withdrawalFilters, status: e.target.value })}
                        className="w-full p-2 md:p-3 text-sm md:text-base border-2 border-border rounded-lg bg-background text-foreground"
                      >
                        <option value="">{trans.earnings?.allStatuses || "All Statuses"}</option>
                        <option value="SUBMITTED">{trans.earnings?.submitted || "Submitted"}</option>
                        <option value="APPROVED">{trans.earnings?.approved || "Approved"}</option>
                        <option value="REJECTED">{trans.earnings?.rejected || "Rejected"}</option>
                        <option value="PROCESSING">{trans.earnings?.processing || "Processing"}</option>
                        <option value="COMPLETED">{trans.earnings?.completed || "Completed"}</option>
                      </select>
                    </div>
                  </div>
                  {selectedRequestIds.length > 0 && (
                    <Button
                      onClick={handleBulkPayout}
                      className="w-full md:w-auto bg-primary hover:bg-primary/90 text-foreground font-semibold text-sm md:text-base py-2 md:py-3"
                    >
                      <FaCheckCircle className="mr-2" />
                      {trans.earnings?.bulkApprove || "Bulk Approve"} ({selectedRequestIds.length} {trans.earnings?.approvedRequests || "approved requests"})
                    </Button>
                  )}
                </div>
              </div>

              {/* Requests Table */}
              {withdrawalRequestsData.data.requests.length > 0 ? (
                <>
                  {/* Mobile Card View */}
                  <div className="block md:hidden space-y-3">
                    {withdrawalRequestsData.data.requests.map((request) => (
                      <div key={request.id} className="bg-card rounded-xl shadow-lg border-2 border-border p-4 space-y-2">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={selectedRequestIds.includes(request.id)}
                              onChange={() => toggleRequestSelection(request.id)}
                              disabled={request.status !== "APPROVED"}
                              className="w-4 h-4 mt-1 disabled:opacity-50 disabled:cursor-not-allowed"
                              title={request.status !== "APPROVED" ? "Only APPROVED requests can be selected for bulk payout" : ""}
                            />
                            <div>
                              <p className="font-semibold text-sm">{request.driver.name}</p>
                              <p className="text-xs text-muted-foreground font-mono">{request.id.slice(0, 8)}...</p>
                            </div>
                          </div>
                          {request.status === "SUBMITTED" && (
                            <Button
                              onClick={() => handleApprove(request)}
                              variant="ghost"
                              size="sm"
                              className="p-2 hover:bg-green-100 text-green-600"
                              title={trans.earnings?.approve || "Approve"}
                            >
                              <FaCheckCircle className="text-sm" />
                            </Button>
                          )}
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-border">
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.amount || "Amount"}</p>
                            <p className="font-bold">{formatCurrency(request.requested_amount ?? 0)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.status || "Status"}</p>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold border ${getStatusColor(request.status)}`}>
                              {request.status}
                            </span>
                          </div>
                        </div>
                        <div className="grid grid-cols-1 gap-2 text-xs pt-2 border-t border-border">
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.email || "Email"}</p>
                            <p className="font-semibold text-foreground break-words">{request.driver.email}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">{trans.earnings?.phone || "Phone"}</p>
                            <p className="font-semibold text-foreground">{request.driver.phone}</p>
                          </div>
                        </div>
                        <div className="pt-2 border-t border-border">
                          <p className="text-xs text-muted-foreground">{trans.earnings?.submittedAt || "Submitted"}: <span className="font-semibold text-foreground">{formatDate(request.created_at)}</span></p>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  {/* Desktop Table View */}
                  <div className="hidden md:block bg-card rounded-xl shadow-xl border-2 border-border overflow-hidden">
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b-2 border-border bg-gray-100 dark:bg-gray-800">
                            <th className="text-start py-4 px-4 font-bold w-12">
                              <input
                                type="checkbox"
                                checked={
                                  withdrawalRequestsData.data.requests.filter(r => r.status === "APPROVED").length > 0 &&
                                  withdrawalRequestsData.data.requests
                                    .filter(r => r.status === "APPROVED")
                                    .every(r => selectedRequestIds.includes(r.id))
                                }
                                onChange={(e) => {
                                  const approvedRequests = withdrawalRequestsData.data.requests.filter(r => r.status === "APPROVED");
                                  if (e.target.checked) {
                                    setSelectedRequestIds(approvedRequests.map((r) => r.id));
                                  } else {
                                    setSelectedRequestIds([]);
                                  }
                                }}
                                className="w-4 h-4"
                              />
                            </th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.requestId || "Request ID"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.driverName || "Driver"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.email || "Email"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.phone || "Phone"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.amount || "Amount"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.status || "Status"}</th>
                            <th className="text-start py-4 px-4 font-bold">{trans.earnings?.submittedAt || "Submitted"}</th>
                            <th className="text-center py-4 px-4 font-bold">{trans.earnings?.actions || "Actions"}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {withdrawalRequestsData.data.requests.map((request) => (
                            <tr key={request.id} className="border-b border-border hover:bg-muted">
                              <td className="py-3 px-4">
                                <input
                                  type="checkbox"
                                  checked={selectedRequestIds.includes(request.id)}
                                  onChange={() => toggleRequestSelection(request.id)}
                                  disabled={request.status !== "APPROVED"}
                                  className="w-4 h-4 disabled:opacity-50 disabled:cursor-not-allowed"
                                  title={request.status !== "APPROVED" ? "Only APPROVED requests can be selected for bulk payout" : ""}
                                />
                              </td>
                              <td className="py-3 px-4 font-mono text-xs">{request.id.slice(0, 8)}...</td>
                              <td className="py-3 px-4 font-semibold">{request.driver.name}</td>
                              <td className="py-3 px-4 text-sm break-words">{request.driver.email}</td>
                              <td className="py-3 px-4 text-sm">{request.driver.phone}</td>
                              <td className="py-3 px-4 font-bold">{formatCurrency(request.requested_amount ?? 0)}</td>
                              <td className="py-3 px-4">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${getStatusColor(request.status)}`}>
                                  {request.status}
                                </span>
                              </td>
                              <td className="py-3 px-4 text-xs">{formatDate(request.created_at)}</td>
                              <td className="py-3 px-4">
                                <div className="flex items-center justify-center gap-2">
                                  {request.status === "SUBMITTED" && (
                                    <Button
                                      onClick={() => handleApprove(request)}
                                      variant="ghost"
                                      className="p-2 hover:bg-green-100 text-green-600"
                                      title={trans.earnings?.approve || "Approve"}
                                    >
                                      <FaCheckCircle />
                                    </Button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                  {withdrawalRequestsData.data.pagination.total_pages > 1 && (
                    <div className="flex justify-center">
                      <Pagination
                        currentPage={withdrawalPage}
                        onPageChange={setWithdrawalPage}
                        locale={locale}
                        totalPages={withdrawalRequestsData.data.pagination.total_pages}
                      />
                    </div>
                  )}
                </>
              ) : (
                <div className="bg-card rounded-xl shadow-xl border-2 border-border p-8 text-center">
                  <p className="text-muted-foreground">{trans.earnings?.noRequests || "No withdrawal requests found"}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-card rounded-xl shadow-xl border-2 border-border p-8 text-center">
              <p className="text-red-600">{trans.earnings?.loadError || "Failed to load withdrawal requests"}</p>
            </div>
          )}
        </div>
      )}

      {/* Approve Modal */}
      <GlobalModal isOpen={showApproveModal} onClose={() => !approveMutation.isPending && setShowApproveModal(false)}>
        <div className="p-4 md:p-6 w-full max-w-md mx-auto">
          <h2 className="text-lg md:text-xl font-bold mb-4">{trans.earnings?.approveRequest || "Approve Withdrawal Request"}</h2>
          <form onSubmit={approveHandleSubmit(onApproveSubmit)} className="space-y-4">
            <div>
              <label className="block text-xs md:text-sm font-medium mb-2">
                {trans.earnings?.adminNote || "Admin Note"} ({trans.earnings?.optional || "Optional"})
              </label>
              <textarea
                {...approveRegister("admin_note")}
                rows={4}
                className="w-full p-2 md:p-3 text-sm md:text-base border-2 border-border rounded-lg bg-background text-foreground"
                placeholder={trans.earnings?.adminNotePlaceholder || "Add a note (optional)"}
              />
            </div>
            <div className="flex flex-col sm:flex-row gap-3 pt-4">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setShowApproveModal(false)}
                disabled={approveMutation.isPending}
                className="flex-1 text-sm md:text-base"
              >
                {trans.earnings?.cancel || "Cancel"}
              </Button>
              <Button
                type="submit"
                disabled={approveMutation.isPending}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white text-sm md:text-base"
              >
                {approveMutation.isPending ? trans.earnings?.approving || "Approving..." : trans.earnings?.approve || "Approve"}
              </Button>
            </div>
          </form>
        </div>
      </GlobalModal>

      {/* Bulk Payout Modal */}
      <GlobalModal isOpen={showBulkPayoutModal} onClose={() => !bulkPayoutMutation.isPending && setShowBulkPayoutModal(false)}>
        <div className="p-4 md:p-6 w-full max-w-md mx-auto">
          <h2 className="text-lg md:text-xl font-bold mb-4">{trans.earnings?.bulkPayout || "Bulk Payout"}</h2>
          <form onSubmit={bulkHandleSubmit(onBulkPayoutSubmit)} className="space-y-4">
            <div>
              <p className="text-xs md:text-sm text-muted-foreground mb-4">
                {trans.earnings?.bulkPayoutDescription || `Processing ${selectedRequestIds.length} selected requests...`}
              </p>
              <input type="hidden" {...bulkRegister("mode")} value="approved_requests" />
              <div className="mb-4">
                <label className="block text-xs md:text-sm font-medium mb-2">
                  {trans.earnings?.driverId || "Driver ID"} ({trans.earnings?.optional || "Optional"})
                </label>
                <input
                  type="number"
                  {...bulkRegister("driver_id", { valueAsNumber: true })}
                  placeholder={trans.earnings?.driverIdPlaceholder || "Filter by specific driver ID (optional)"}
                  className="w-full p-2 md:p-3 text-sm md:text-base border-2 border-border rounded-lg bg-background text-foreground"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {trans.earnings?.driverIdHint || "Leave empty to process all selected requests, or specify a driver ID to filter"}
                </p>
            </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-3 pt-4">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setShowBulkPayoutModal(false)}
                disabled={bulkPayoutMutation.isPending}
                className="flex-1 text-sm md:text-base"
              >
                {trans.earnings?.cancel || "Cancel"}
              </Button>
              <Button
                type="submit"
                disabled={bulkPayoutMutation.isPending}
                className="flex-1 bg-primary hover:bg-primary/90 text-foreground text-sm md:text-base"
              >
                {bulkPayoutMutation.isPending ? trans.earnings?.processing || "Processing..." : trans.earnings?.processPayout || "Process Payout"}
              </Button>
            </div>
          </form>
        </div>
      </GlobalModal>
    </div>
  );
}
