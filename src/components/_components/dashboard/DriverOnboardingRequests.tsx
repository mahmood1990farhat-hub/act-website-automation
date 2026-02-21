"use client";

import { Button } from "@/components/ui/button";
import { fetchData } from "@/lib/api/fetchData";
import { postData } from "@/lib/api/postData";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { Locale } from "../../../../i18n.config";
import IsLoadig from "../ISloading";
import { BsEyeFill } from "react-icons/bs";
import { FaClock, FaCheckCircle, FaTimesCircle, FaUserTie, FaSearch, FaDownload, FaEye } from "react-icons/fa";
import { formatDate } from "@/lib/FormatDate";
import GlobalModal from "../GlobalModal";
import { toast } from "react-toastify";
import Pagination from "../Pagination";
import { extract_error } from "@/lib/api/errorApi";

type OnboardingRequest = {
  id: number;
  full_name: string;
  mobile_number: string;
  email_address: string;
  home_postcode: string;
  preferred_communication: string;
  years_experience: string;
  previous_companies: string[];
  familiar_areas: string[] | string;
  preferred_journey_types: string[];
  vehicle_ownership: string;
  vehicle_type: string;
  fuel_type: string;
  preferred_locations: string[];
  availability: string;
  notification_method: string;
  has_tfl_licence: boolean;
  willing_dbs_check: boolean;
  agrees_policies: boolean;
  status: "pending" | "step1_approved" | "step1_rejected" | "documents_uploaded" | "final_approved" | "final_rejected" | "needs_modification";
  admin_notes: string;
  rejection_reason: string;
  reviewed_by: number | null;
  reviewed_at: string | null;
  created_at: string;
  user_email: string;
  user_username: string;
  documents?: {
    pco?: {
      content: string;
      filename: string;
      extension: string;
      size: number;
    };
    dbs?: {
      content: string;
      filename: string;
      extension: string;
      size: number;
    };
    dvla?: {
      content: string;
      filename: string;
      extension: string;
      size: number;
    };
    bank_details?: {
      bank_account_number: string;
      sort_code: string;
      registered_address: string;
    };
    vehicle?: {
      vehicle_number: string;
      year_of_manufacture: number;
      mot?: {
        content: string;
        filename: string;
        extension: string;
        size: number;
      };
      phv?: {
        content: string;
        filename: string;
        extension: string;
        size: number;
      };
      insurance?: {
        content: string;
        filename: string;
        extension: string;
        size: number;
      };
    };
  };
};

type OnboardingResponse = {
  data: OnboardingRequest[];
  total_count: number;
  pending_count: number;
  step1_approved_count: number;
  documents_uploaded_count: number;
  final_approved_count: number;
  final_rejected_count: number;
  step1_rejected_count: number;
  needs_modification_count: number;
  pagination?: {
    count: number;
    num_pages: number;
    current_page: number;
    page_size: number;
  };
};

function getStatusColor(status: string) {
  switch (status) {
    case "pending":
      return "bg-yellow-500/20 text-yellow-600 border-yellow-500";
    case "step1_approved":
      return "bg-green-500/20 text-green-600 border-green-500";
    case "step1_rejected":
      return "bg-red-500/20 text-red-600 border-red-500";
    case "documents_uploaded":
      return "bg-blue-500/20 text-blue-600 border-blue-500";
    case "final_approved":
      return "bg-emerald-500/20 text-emerald-600 border-emerald-500";
    case "final_rejected":
      return "bg-rose-500/20 text-rose-600 border-rose-500";
    case "needs_modification":
      return "bg-orange-500/20 text-orange-600 border-orange-500";
    default:
      return "bg-gray-500/20 text-gray-600 border-gray-500";
  }
}

export default function DriverOnboardingRequests({
  token,
  locale,
  trans,
}: {
  token?: string;
  locale: Locale;
  trans: any;
}) {
  const [selectedRequestId, setSelectedRequestId] = useState<number | null>(null);
  const [openDetails, setOpenDetails] = useState(false);
  const [actionModal, setActionModal] = useState<{
    open: boolean;
    type: "approve" | "reject" | "modify" | null;
    requestId: number | null;
    isFinalReview: boolean;
  }>({ open: false, type: null, requestId: null, isFinalReview: false });
  const [imagePreview, setImagePreview] = useState<{
    open: boolean;
    url: string;
    title: string;
  }>({ open: false, url: "", title: "" });
  const [notes, setNotes] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [filesToModify, setFilesToModify] = useState<string[]>([]);
  const [filterStatus, setFilterStatus] = useState<OnboardingRequest["status"] | "all">("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 6;

  const queryClient = useQueryClient();

  // Debounce search term
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, 500);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Fetch unfiltered statistics for cards (always fetch all data for statistics)
  const { data: statisticsData } = useQuery<OnboardingResponse>({
    queryKey: ["driver-onboarding-statistics"],
    queryFn: () => {
      return fetchData({
        endpoint: "/api/drivers/admin/onboarding-requests/",
        token: token,
        queryParams: { locale: locale },
      });
    },
  });

  // Fetch filtered data for the table/list
  const { data: onboardingData, isLoading } = useQuery<OnboardingResponse>({
    queryKey: ["driver-onboarding-requests", filterStatus, debouncedSearchTerm, page, pageSize],
    queryFn: () => {
      const params: Record<string, string> = {
        locale: locale,
        page: page.toString(),
        page_size: pageSize.toString(),
      };
      if (filterStatus !== "all") {
        params.status = filterStatus;
      }
      if (debouncedSearchTerm.trim()) {
        params.search = debouncedSearchTerm.trim();
      }
      return fetchData({
        endpoint: "/api/drivers/admin/onboarding-requests/",
        token: token,
        queryParams: params,
      });
    },
  });

  // Fetch detailed data for selected request
  const { data: selectedRequest, isLoading: isLoadingDetails } = useQuery<OnboardingRequest>({
    queryKey: ["driver-onboarding-request-details", selectedRequestId],
    queryFn: () => {
      return fetchData({
        endpoint: `/api/drivers/admin/onboarding-requests/${selectedRequestId}/`,
        token: token,
        queryParams: { locale: locale },
      });
    },
    enabled: !!selectedRequestId && openDetails,
  });

  const actionMutation = useMutation({
    mutationFn: async ({
      requestId,
      action,
      notes,
      rejectionReason,
      isFinalReview,
      filesToModify,
    }: {
      requestId: number;
      action: "approve" | "reject" | "modify";
      notes: string;
      rejectionReason?: string;
      isFinalReview: boolean;
      filesToModify?: string[];
    }) => {
      const body: any = { action };
      
      // For modify action in final review, use the new format
      if (action === "modify" && isFinalReview) {
        body.rejection_reason = rejectionReason || "";
        body.files_to_modify = filesToModify || [];
      } else {
        // For other actions, use the old format
        body.notes = notes;
        if ((action === "reject" || action === "modify") && rejectionReason) {
          body.rejection_reason = rejectionReason;
        }
      }
      
      const endpoint = isFinalReview
        ? `/api/drivers/admin/onboarding-requests/${requestId}/final-review/`
        : `/api/drivers/admin/onboarding-requests/${requestId}/action/`;
      
      return postData({
        endpoint,
        body,
        token,
        queryParams: { locale },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["driver-onboarding-requests"] });
      queryClient.invalidateQueries({ queryKey: ["driver-onboarding-statistics"] });
      queryClient.invalidateQueries({ queryKey: ["driver-onboarding-request-details"] });
      setActionModal({ open: false, type: null, requestId: null, isFinalReview: false });
      setOpenDetails(false);
      setSelectedRequestId(null);
      setNotes("");
      setRejectionReason("");
      setFilesToModify([]);
    },
    onError: () => {
      // Error toast is handled by postData
    },
  });

  const handleAction = () => {
    if (!actionModal.requestId || !actionModal.type) return;
    
    if ((actionModal.type === "reject" || actionModal.type === "modify") && !rejectionReason.trim()) {
      toast.error(trans.rejectionReasonRequired || "Rejection reason is required");
      return;
    }

    // For modify action in final review, files_to_modify is required
    if (actionModal.type === "modify" && actionModal.isFinalReview && filesToModify.length === 0) {
      toast.error(trans.filesToModifyRequired || "Please select at least one file that needs modification");
      return;
    }

    actionMutation.mutate({
      requestId: actionModal.requestId,
      action: actionModal.type,
      notes: notes.trim(),
      rejectionReason: rejectionReason.trim(),
      isFinalReview: actionModal.isFinalReview,
      filesToModify: actionModal.type === "modify" && actionModal.isFinalReview ? filesToModify : undefined,
    });
  };

  // Get data directly from API (already filtered on server-side)
  const filteredRequests = onboardingData?.data || [];
  const paginationInfo = onboardingData?.pagination;
  const totalPages = paginationInfo?.num_pages || 1;

  const handleStatusFilter = (status: OnboardingRequest["status"] | "all") => {
    setFilterStatus(status);
    setPage(1);
  };

  useEffect(() => {
    if (paginationInfo && paginationInfo.num_pages > 0 && page > paginationInfo.num_pages) {
      setPage(paginationInfo.num_pages);
    }
  }, [paginationInfo, page]);

  // Get statistics from the unfiltered data (for cards display)
  const totalCount = statisticsData?.total_count || 0;
  const pendingCount = statisticsData?.pending_count || 0;
  const approvedCount = statisticsData?.step1_approved_count || 0;
  const rejectedCount = statisticsData?.step1_rejected_count || 0;
  const documentsUploadedCount = statisticsData?.documents_uploaded_count || 0;
  const finalApprovedCount = statisticsData?.final_approved_count || 0;
  const finalRejectedCount = statisticsData?.final_rejected_count || 0;
  const needsModificationCount = statisticsData?.needs_modification_count || 0;

  const humanizeStatus = (value: OnboardingRequest["status"]) =>
    value
      .replace(/_/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .replace(/\b\w/g, (char) => char.toUpperCase());

  const resolveStatusTitle = (value: OnboardingRequest["status"]) => {
    const driverStatusTitles = trans?.statusTitles || {};
    if (driverStatusTitles[value]) {
      return driverStatusTitles[value];
    }
    return humanizeStatus(value);
  };

  const statusDescriptions = trans?.statusDescriptions || {};

  const statusFlow: Array<{
    value: Exclude<OnboardingRequest["status"], "step1_rejected" | "final_rejected" | "needs_modification">;
    title: string;
    description: string;
  }> = [
    {
      value: "pending",
      title: resolveStatusTitle("pending"),
      description: statusDescriptions.pending || "Application submitted and awaiting the initial review.",
    },
    {
      value: "step1_approved",
      title: resolveStatusTitle("step1_approved"),
      description:
        statusDescriptions.step1_approved || "Initial profile and eligibility checks have been approved.",
    },
    {
      value: "documents_uploaded",
      title: resolveStatusTitle("documents_uploaded"),
      description:
        statusDescriptions.documents_uploaded ||
        "Driver uploaded the required compliance documents for review.",
    },
    {
      value: "final_approved",
      title: resolveStatusTitle("final_approved"),
      description:
        statusDescriptions.final_approved || "Final review completed. The driver can now be activated.",
    },
  ];

  const statusRank: Record<OnboardingRequest["status"], number> = {
    pending: 0,
    step1_approved: 1,
    documents_uploaded: 2,
    final_approved: 3,
    final_rejected: 3,
    step1_rejected: 1,
    needs_modification: 2,
  };

  const currentStatusRank = selectedRequest ? statusRank[selectedRequest.status] ?? 0 : 0;
  const isRejectedStatus = selectedRequest
    ? selectedRequest.status === "step1_rejected" || selectedRequest.status === "final_rejected"
    : false;
  const isModificationStatus = selectedRequest?.status === "needs_modification";

  return (
    <>
      <div className="min-h-screen bg-gradient-to-b from-background via-background/90 to-background px-2 sm:px-4 py-6 space-y-6">
      {/* Statistics Cards - Compact & Professional */}
      <div className="mt-5">
        {/* <h2 className="mb-3 text-base font-semibold text-foreground">{trans.statistics || "Statistics"}</h2> */}
        {statisticsData && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {/* Total Requests Card */}
            <button
              onClick={() => handleStatusFilter("all")}
              className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
                filterStatus === "all"
                  ? "border-yellow-500 shadow-xl shadow-yellow-500/30 scale-105"
                  : "border-yellow-500/60 hover:border-yellow-500/80 hover:shadow-lg hover:shadow-yellow-500/20"
              }`}
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-yellow-500/30">
                  <FaUserTie className="text-foreground text-2xl" />
                </div>
                <div className="flex-1 grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">{trans.totalRequests || "Total"}</p>
                    <p className="text-2xl font-bold text-yellow-600">{totalCount}</p>
                  </div>
                  <div className="border-l-2 border-border pl-3">
                    <p className="text-xs font-medium text-muted-foreground mb-1">{trans.activeLabel || "Active"}</p>
                    <p className="text-2xl font-bold text-foreground">{pendingCount + approvedCount}</p>
                  </div>
                </div>
              </div>
            </button>

            {/* Pending Card */}
            <button
              onClick={() => handleStatusFilter("pending")}
              className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
                filterStatus === "pending"
                  ? "border-yellow-400 shadow-xl shadow-yellow-400/30 scale-105"
                  : "border-yellow-400/60 hover:border-yellow-400/80 hover:shadow-lg hover:shadow-yellow-400/20"
              }`}
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-yellow-500/30">
                  <FaClock className="text-foreground text-2xl" />
                </div>
                <div className="flex-1 grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">{trans.pendingRequests || "Pending"}</p>
                    <p className="text-2xl font-bold text-yellow-600">{pendingCount}</p>
                  </div>
                  <div className="border-l-2 border-border pl-3">
                    <p className="text-xs font-medium text-muted-foreground mb-1">{trans.percentLabel || "% of Total"}</p>
                    <p className="text-2xl font-bold text-foreground">
                      {totalCount > 0 ? Math.round((pendingCount / totalCount) * 100) : 0}%
                    </p>
                  </div>
                </div>
              </div>
            </button>

            {/* Approved Card */}
            <button
              onClick={() => handleStatusFilter("step1_approved")}
              className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
                filterStatus === "step1_approved"
                  ? "border-green-500 shadow-xl shadow-green-500/30 scale-105"
                  : "border-green-500/60 hover:border-green-500/80 hover:shadow-lg hover:shadow-green-500/20"
              }`}
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-green-500/30">
                  <FaCheckCircle className="text-white text-2xl" />
                </div>
                <div className="flex-1 grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">{trans.approvedRequests || "Approved"}</p>
                    <p className="text-2xl font-bold text-green-600">{approvedCount}</p>
                  </div>
                  <div className="border-l-2 border-border pl-3">
                    <p className="text-xs font-medium text-muted-foreground mb-1">{trans.percentLabel || "% of Total"}</p>
                    <p className="text-2xl font-bold text-foreground">
                      {totalCount > 0 ? Math.round((approvedCount / totalCount) * 100) : 0}%
                    </p>
                  </div>
                </div>
              </div>
            </button>

            {/* Rejected Card */}
            <button
              onClick={() => handleStatusFilter("step1_rejected")}
              className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
                filterStatus === "step1_rejected"
                  ? "border-red-500 shadow-xl shadow-red-500/30 scale-105"
                  : "border-red-500/60 hover:border-red-500/80 hover:shadow-lg hover:shadow-red-500/20"
              }`}
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-red-500/30">
                  <FaTimesCircle className="text-white text-2xl" />
                </div>
                <div className="flex-1 grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">{trans.step1Rejected || "Step 1 Rejected"}</p>
                    <p className="text-2xl font-bold text-red-600">{rejectedCount}</p>
                  </div>
                  <div className="border-l-2 border-border pl-3">
                    <p className="text-xs font-medium text-muted-foreground mb-1">{trans.percentLabel || "% of Total"}</p>
                    <p className="text-2xl font-bold text-foreground">
                      {totalCount > 0 ? Math.round((rejectedCount / totalCount) * 100) : 0}%
                    </p>
                  </div>
                </div>
              </div>
            </button>

            {/* Documents Uploaded Card */}
            <button
              onClick={() => handleStatusFilter("documents_uploaded")}
              className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
                filterStatus === "documents_uploaded"
                  ? "border-blue-500 shadow-xl shadow-blue-500/30 scale-105"
                  : "border-blue-500/60 hover:border-blue-500/80 hover:shadow-lg hover:shadow-blue-500/20"
              }`}
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/30">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-xs font-medium text-muted-foreground mb-1">{trans.documentsUploaded || "Docs Uploaded"}</p>
                  <p className="text-2xl font-bold text-blue-600">{documentsUploadedCount}</p>
                </div>
              </div>
            </button>

            {/* Final Approved Card */}
            <button
              onClick={() => handleStatusFilter("final_approved")}
              className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
                filterStatus === "final_approved"
                  ? "border-emerald-500 shadow-xl shadow-emerald-500/30 scale-105"
                  : "border-emerald-500/60 hover:border-emerald-500/80 hover:shadow-lg hover:shadow-emerald-500/20"
              }`}
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-emerald-500/30">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-xs font-medium text-muted-foreground mb-1">{trans.finalApproved || "Final Approved"}</p>
                  <p className="text-2xl font-bold text-emerald-600">{finalApprovedCount}</p>
                </div>
              </div>
            </button>

            {/* Final Rejected Card */}
            <button
              onClick={() => handleStatusFilter("final_rejected")}
              className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
                filterStatus === "final_rejected"
                  ? "border-rose-500 shadow-xl shadow-rose-500/30 scale-105"
                  : "border-rose-500/60 hover:border-rose-500/80 hover:shadow-lg hover:shadow-rose-500/20"
              }`}
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-rose-500 to-rose-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-rose-500/30">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-xs font-medium text-muted-foreground mb-1">{trans.finalRejected || "Final Rejected"}</p>
                  <p className="text-2xl font-bold text-rose-600">{finalRejectedCount}</p>
                </div>
              </div>
            </button>

            {/* Needs Modification Card */}
            <button
              onClick={() => handleStatusFilter("needs_modification")}
              className={`group bg-card rounded-xl border-2 p-4 transition-all duration-300 text-left ${
                filterStatus === "needs_modification"
                  ? "border-orange-500 shadow-xl shadow-orange-500/30 scale-105"
                  : "border-orange-500/60 hover:border-orange-500/80 hover:shadow-lg hover:shadow-orange-500/20"
              }`}
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-orange-500/30">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-xs font-medium text-muted-foreground mb-1">{trans.needsModification || "Needs Modification"}</p>
                  <p className="text-2xl font-bold text-orange-600">{needsModificationCount}</p>
                </div>
              </div>
            </button>
          </div>
        )}

        {/* Search Bar */}
        <div className="my-6">
          <div className="relative max-w-md">
            <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder={trans.searchPlaceholder || "Search by name, email, phone..."}
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              className="w-full pl-10 pr-4 py-3 rounded-lg bg-card border-2 border-border text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none transition-all"
            />
            {searchTerm && (
              <button
                onClick={() => {
                  setSearchTerm("");
                  setPage(1);
                }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Requests Table - Desktop View - Enhanced Colors */}
        <div className="my-5 hidden xl:block">
          <div className="w-full bg-card rounded-xl shadow-xl border-2 border-border overflow-hidden">
            <div className="bg-gradient-to-r from-card to-background px-6 py-3 border-b-2 border-border">
              <h2 className="text-foreground text-base font-bold drop-shadow-sm">
                {trans.allRequests || "All Requests"}
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b-2 border-border bg-card">
                    <th className="text-start py-3 px-3 font-bold text-foreground">{trans.tableHeaders?.[0] || "Full Name"}</th>
                    <th className="text-start py-3 px-3 font-bold text-foreground">{trans.tableHeaders?.[1] || "Email"}</th>
                    <th className="text-start py-3 px-3 font-bold text-foreground">{trans.tableHeaders?.[2] || "Phone"}</th>
                    <th className="text-start py-3 px-3 font-bold text-foreground">{trans.tableHeaders?.[3] || "Experience"}</th>
                    <th className="text-start py-3 px-3 font-bold text-foreground">{trans.tableHeaders?.[4] || "Vehicle"}</th>
                    <th className="text-start py-3 px-3 font-bold text-foreground">{trans.tableHeaders?.[5] || "Applied Date"}</th>
                    <th className="text-start py-3 px-3 font-bold text-foreground">{trans.tableHeaders?.[6] || "Status"}</th>
                    <th className="text-center py-3 px-3 font-bold text-foreground">{trans.tableHeaders?.[7] || "Action"}</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    <tr>
                      <td colSpan={8}>
                        <IsLoadig />
                      </td>
                    </tr>
                  ) : filteredRequests && filteredRequests.length > 0 ? (
                    filteredRequests.map((request) => (
                      <tr
                        key={request.id}
                        className="border-b border-border hover:bg-muted transition-colors"
                      >
                        <td className="py-3 px-3 font-bold text-foreground max-w-[160px]">
                          <div className="truncate" title={request.full_name}>
                            {request.full_name}
                          </div>
                        </td>
                        <td className="py-3 px-3 text-foreground max-w-[140px]">
                          <div className="truncate" title={request.email_address}>
                            {request.email_address}
                          </div>
                        </td>
                        <td className="py-3 px-3 text-foreground whitespace-nowrap">
                          {request.mobile_number}
                        </td>
                        <td className="py-3 px-3 capitalize text-foreground whitespace-nowrap">
                          {request.years_experience.replace(/_/g, " ")}
                        </td>
                        <td className="py-3 px-3 text-foreground max-w-[140px]">
                          <div className="truncate" title={request.vehicle_type}>
                            {request.vehicle_type}
                          </div>
                        </td>
                        <td className="py-3 px-3 text-muted-foreground whitespace-nowrap">
                          {formatDate(new Date(request.created_at), locale)}
                        </td>
                        <td className="py-3 px-3 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${getStatusColor(
                              request.status
                            )}`}
                          >
                            {resolveStatusTitle(request.status)}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center whitespace-nowrap">
                          <Button
                            onClick={() => {
                              setSelectedRequestId(request.id);
                              setOpenDetails(true);
                            }}
                            variant="ghost"
                            className="p-1.5 hover:bg-muted text-yellow-600 hover:text-yellow-700 transition-colors inline-flex"
                          >
                            <BsEyeFill className="text-base" />
                          </Button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-muted-foreground">
                        {trans.noRequests || "No requests found"}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {!isLoading && filteredRequests.length > 0 && totalPages > 1 && (
          <div className="hidden xl:flex items-center justify-between px-2 sm:px-4">
            <span className="text-xs text-muted-foreground">
              {trans.pagination?.table || "Table"} {paginationInfo?.current_page || page} {trans.pagination?.of || "of"} {totalPages} {trans.pagination?.tables || "tables"}
            </span>
            <Pagination
              currentPage={paginationInfo?.current_page || page}
              onPageChange={(next) => setPage(next)}
              locale={locale}
              totalPages={totalPages}
            />
          </div>
        )}

        {/* Requests Cards - Mobile View - Enhanced Colors */}
        <div className="my-5 xl:hidden space-y-4">
          {isLoading ? (
            <IsLoadig />
          ) : filteredRequests && filteredRequests.length > 0 ? (
            filteredRequests.map((request) => (
              <div
                key={request.id}
                className="bg-card rounded-xl shadow-lg border-2 border-border p-4 hover:shadow-2xl hover:border-primary/60 transition-all"
              >
                {/* Header with name and status */}
                <div className="flex items-start justify-between mb-3 pb-3 border-b-2 border-border">
                  <div className="flex-1">
                    <h3 className="font-bold text-lg text-foreground mb-1">{request.full_name}</h3>
                    <p className="text-sm text-muted-foreground">{request.email_address}</p>
                  </div>
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border ${getStatusColor(
                      request.status
                    )}`}
                  >
                    {resolveStatusTitle(request.status)}
                  </span>
                </div>

                {/* Details Grid */}
                <div className="space-y-2 mb-4">
                  <div className="flex items-center justify-between py-2 border-b border-border">
                    <span className="text-sm text-muted-foreground font-semibold">{trans.tableHeaders?.[2] || "Phone"}:</span>
                    <span className="text-sm text-foreground font-bold">{request.mobile_number}</span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-border">
                    <span className="text-sm text-muted-foreground font-semibold">{trans.tableHeaders?.[3] || "Experience"}:</span>
                    <span className="text-sm text-foreground font-bold capitalize">
                      {request.years_experience.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-border">
                    <span className="text-sm text-muted-foreground font-semibold">{trans.tableHeaders?.[4] || "Vehicle"}:</span>
                    <span className="text-sm text-foreground font-bold">{request.vehicle_type}</span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-muted-foreground font-semibold">{trans.tableHeaders?.[5] || "Applied Date"}:</span>
                    <span className="text-sm text-foreground font-bold">
                      {formatDate(new Date(request.created_at), locale)}
                    </span>
                  </div>
                </div>

                {/* Action Button */}
                <Button
                  onClick={() => {
                    setSelectedRequestId(request.id);
                    setOpenDetails(true);
                  }}
                  className="w-full bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-foreground font-bold shadow-lg shadow-yellow-500/20"
                >
                  <FaEye className="mr-2" />
                  {trans.viewDetails || "View Details"}
                </Button>
              </div>
            ))
          ) : (
            <div className="bg-card rounded-xl shadow-lg border-2 border-border p-8 text-center">
              <p className="text-muted-foreground font-medium">{trans.noRequests || "No requests found"}</p>
            </div>
          )}
        </div>

        {!isLoading && filteredRequests.length > 0 && totalPages > 1 && (
          <div className="xl:hidden flex items-center justify-between px-2">
            <span className="text-xs text-muted-foreground">
              {trans.pagination?.table || "Table"} {paginationInfo?.current_page || page} {trans.pagination?.of || "of"} {totalPages} {trans.pagination?.tables || "tables"}
            </span>
            <Pagination
              currentPage={paginationInfo?.current_page || page}
              onPageChange={(next) => setPage(next)}
              locale={locale}
              totalPages={totalPages}
            />
          </div>
        )}
      </div>
      </div>

      {/* Request Details Modal - Dark Theme */}
      {openDetails && (
        <div
          onClick={() => {
            setOpenDetails(false);
            setSelectedRequestId(null);
          }}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-3 lg:p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-card rounded-2xl w-full max-w-4xl shadow-2xl max-h-[95vh] xl:max-h-[90vh] overflow-y-auto on-scrollbar border-2 border-border"
          >
            {/* Modal Header */}
            <div className="sticky top-0 bg-gradient-to-r from-card to-background px-4 xl:px-6 py-4 lg:py-5 border-b-2 border-border rounded-t-2xl z-10">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <h2 className="text-xl lg:text-2xl font-bold text-foreground">
                  {trans.requestDetails || "Request Details"}
                </h2>
                {selectedRequest && (
                  <span
                    className={`px-4 py-2 rounded-full text-xs xl:text-sm font-bold border ${getStatusColor(
                      selectedRequest.status
                    )}`}
                  >
                    {resolveStatusTitle(selectedRequest.status)}
                  </span>
                )}
              </div>
            </div>

            {selectedRequest && (
              <div className="px-4 xl:px-6 py-4 bg-card/40 border-b border-border">
                <h3 className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">
                  {trans.statusFlowTitle || "Review Progress"}
                </h3>
                <p className="text-sm text-muted-foreground mt-2">
                  {trans.statusFlowSubtitle ||
                    "Track where this application currently stands in the onboarding process."}
                </p>
                <div className="mt-4 flex flex-col gap-4">
                  <div className="flex items-center gap-2">
                    {statusFlow.map((step, idx) => {
                      const stepRank = statusRank[step.value];
                      const state =
                        currentStatusRank > stepRank
                          ? "completed"
                          : currentStatusRank === stepRank
                          ? "current"
                          : "upcoming";
                      return (
                        <div key={step.value} className="flex items-center gap-2 flex-1 min-w-0">
                          <div className="flex flex-col items-center min-w-0">
                            <div
                              className={`relative w-9 h-9 sm:w-11 sm:h-11 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                                state === "completed"
                                  ? "bg-emerald-500 text-white shadow-lg shadow-emerald-500/30"
                                  : state === "current"
                                  ? "bg-primary text-black shadow-lg shadow-primary/30"
                                  : "bg-muted text-muted-foreground border border-border"
                              }`}
                            >
                              {state === "completed" ? (
                                <FaCheckCircle className="text-white text-sm sm:text-base" />
                              ) : (
                                idx + 1
                              )}
                              {state === "current" && (
                                <span className="absolute inset-0 rounded-full border-2 border-primary/40 animate-ping" />
                              )}
                            </div>
                            <span
                              className={`mt-2 text-[10px] sm:text-xs font-semibold text-center leading-tight ${
                                state !== "upcoming" ? "text-primary" : "text-muted-foreground"
                              }`}
                            >
                              {step.title}
                            </span>
                            <span className="hidden md:block text-[11px] text-muted-foreground text-center leading-tight mt-1 px-2">
                              {step.description}
                            </span>
                          </div>
                          {idx < statusFlow.length - 1 && (
                            <div
                              className={`flex-1 h-0.5 rounded-full transition-colors duration-300 ${
                                currentStatusRank > stepRank ? "bg-primary" : "bg-border"
                              }`}
                            />
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {(isRejectedStatus || isModificationStatus) && (
                    <div
                      className={`flex items-center gap-2 text-xs font-semibold px-3 py-2 rounded-lg border ${
                        isModificationStatus
                          ? "bg-orange-500/10 border-orange-500/30 text-orange-400"
                          : "bg-red-500/10 border-red-500/30 text-red-400"
                      }`}
                    >
                      {isModificationStatus
                        ? `${trans.modificationBadge || "Awaiting driver updates"} — ${resolveStatusTitle(
                            selectedRequest.status
                          )}`
                        : `${trans.rejectionBadge || "Rejected at this stage"} — ${resolveStatusTitle(
                            selectedRequest.status
                          )}`}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Modal Content */}
            {isLoadingDetails ? (
              <div className="p-4 md:p-6">
                <IsLoadig />
              </div>
            ) : selectedRequest ? (
            <>
            <div className="p-4 md:p-6 space-y-5 md:space-y-6">
              {/* Personal Information */}
              <div className="bg-muted border-2 border-yellow-500/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-yellow-500 rounded-full"></span>
                  {trans.personalInfo || "Personal Information"}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">{trans.fullName || "Full Name"}</p>
                    <p className="font-semibold text-foreground text-sm md:text-base">{selectedRequest.full_name}</p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">{trans.email || "Email"}</p>
                    <p className="font-semibold text-foreground text-sm md:text-base break-all">{selectedRequest.email_address}</p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">{trans.phone || "Phone"}</p>
                    <p className="font-semibold text-foreground text-sm md:text-base">{selectedRequest.mobile_number}</p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">{trans.postcode || "Postcode"}</p>
                    <p className="font-semibold text-foreground text-sm md:text-base">{selectedRequest.home_postcode}</p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border sm:col-span-2">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.preferredComm || "Preferred Communication"}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base capitalize">{selectedRequest.preferred_communication}</p>
                  </div>
                </div>
              </div>

              {/* Driving Experience */}
              <div className="bg-muted border-2 border-blue-400/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-blue-500 rounded-full"></span>
                  {trans.drivingExp || "Driving Experience"}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">{trans.yearsExp || "Years of Experience"}</p>
                    <p className="font-semibold text-foreground text-sm md:text-base capitalize">
                      {selectedRequest.years_experience.replace(/_/g, " ")}
                    </p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">{trans.previousCompanies || "Previous Companies"}</p>
                    <p className="font-semibold text-foreground text-sm md:text-base">
                      {selectedRequest.previous_companies.join(", ") || "None"}
                    </p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border sm:col-span-2">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">{trans.familiarAreas || "Familiar Areas"}</p>
                    <p className="font-semibold text-foreground text-sm md:text-base">{selectedRequest.familiar_areas}</p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border sm:col-span-2">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-2">
                      {trans.preferredJourneys || "Preferred Journey Types"}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {selectedRequest.preferred_journey_types.map((type, idx) => (
                        <span
                          key={idx}
                          className="px-3 py-1.5 bg-yellow-500/20 text-yellow-600 border border-yellow-500/50 rounded-full text-xs md:text-sm font-semibold"
                        >
                          {type}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Vehicle Information */}
              <div className="bg-muted border-2 border-purple-400/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-purple-500 rounded-full"></span>
                  {trans.vehicleInfo || "Vehicle Information"}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">{trans.ownership || "Ownership"}</p>
                    <p className="font-semibold text-foreground text-sm md:text-base capitalize">{selectedRequest.vehicle_ownership}</p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">{trans.vehicleType || "Vehicle Type"}</p>
                    <p className="font-semibold text-foreground text-sm md:text-base">{selectedRequest.vehicle_type}</p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">{trans.fuelType || "Fuel Type"}</p>
                    <p className="font-semibold text-foreground text-sm md:text-base capitalize">{selectedRequest.fuel_type}</p>
                  </div>
                </div>
              </div>

              {/* Preferences & Availability */}
              <div className="bg-muted border-2 border-emerald-400/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-emerald-500 rounded-full"></span>
                  {trans.preferencesAvailability || "Preferences & Availability"}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.preferredLocations || "Preferred Locations"}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base">{selectedRequest.preferred_locations.join(", ")}</p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">{trans.availability || "Availability"}</p>
                    <p className="font-semibold text-foreground text-sm md:text-base capitalize">
                      {selectedRequest.availability.replace(/_/g, " ")}
                    </p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border sm:col-span-2">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.notificationMethod || "Notification Method"}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base capitalize">{selectedRequest.notification_method}</p>
                  </div>
                </div>
              </div>

              {/* Compliance */}
              <div className="bg-muted border-2 border-indigo-400/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-indigo-500 rounded-full"></span>
                  {trans.compliance || "Compliance & Safety"}
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center gap-3 bg-card p-3 rounded-lg border border-border">
                    {selectedRequest.has_tfl_licence ? (
                      <FaCheckCircle className="text-green-500 text-xl flex-shrink-0" />
                    ) : (
                      <FaTimesCircle className="text-red-500 text-xl flex-shrink-0" />
                    )}
                    <span className="font-semibold text-foreground text-sm md:text-base">{trans.tflLicence || "Has TfL Licence"}</span>
                  </div>
                  <div className="flex items-center gap-3 bg-card p-3 rounded-lg border border-border">
                    {selectedRequest.willing_dbs_check ? (
                      <FaCheckCircle className="text-green-500 text-xl flex-shrink-0" />
                    ) : (
                      <FaTimesCircle className="text-red-500 text-xl flex-shrink-0" />
                    )}
                    <span className="font-semibold text-foreground text-sm md:text-base">{trans.dbsCheck || "Willing to undergo DBS Check"}</span>
                  </div>
                  <div className="flex items-center gap-3 bg-card p-3 rounded-lg border border-border">
                    {selectedRequest.agrees_policies ? (
                      <FaCheckCircle className="text-green-500 text-xl flex-shrink-0" />
                    ) : (
                      <FaTimesCircle className="text-red-500 text-xl flex-shrink-0" />
                    )}
                    <span className="font-semibold text-foreground text-sm md:text-base">{trans.agreesPolicies || "Agrees to Policies"}</span>
                  </div>
                </div>
              </div>

              {/* Uploaded Documents */}
              {(selectedRequest.status === "documents_uploaded" || 
                selectedRequest.status === "final_approved" || 
                selectedRequest.status === "final_rejected" ||
                selectedRequest.status === "needs_modification") && (
                <div className="bg-muted border-2 border-purple-400/50 rounded-xl p-4 md:p-5">
                  <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                    <span className="w-1 h-6 bg-purple-500 rounded-full"></span>
                    {trans.uploadedDocuments || "Uploaded Documents"}
                  </h3>
                  
                  {selectedRequest.documents ? (
                  <div className="space-y-6">
                    {/* Driver Documents */}
                    <div>
                      <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        {trans.driverDocuments || "Driver Documents"}
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {/* PCO Licence */}
                        {selectedRequest.documents.pco && (() => {
                          const mimeType = selectedRequest.documents.pco!.extension.toLowerCase().includes('png') ? 'image/png' : 
                                          selectedRequest.documents.pco!.extension.toLowerCase().includes('jpg') || 
                                          selectedRequest.documents.pco!.extension.toLowerCase().includes('jpeg') ? 'image/jpeg' : 
                                          'application/octet-stream';
                          const dataUrl = `data:${mimeType};base64,${selectedRequest.documents.pco!.content}`;
                          
                          return (
                            <div className="bg-card p-3 rounded-lg border border-border">
                              <div className="flex items-start justify-between mb-2">
                                <p className="text-xs md:text-sm font-medium text-muted-foreground">{trans.pcoLicence || "PCO Licence"}</p>
                                <span className="text-xs text-green-600 font-semibold">{(selectedRequest.documents.pco!.size / 1024).toFixed(1)} KB</span>
                              </div>
                            <p className="text-[11px] text-muted-foreground/80 mb-2">
                              {trans.pcoLicenceDesc ||
                                "Private Hire Vehicle (PCO) licence issued by TfL showing the driver is authorised to operate."}
                            </p>
                              <p className="text-xs text-foreground mb-3 truncate" title={selectedRequest.documents.pco!.filename}>
                                {selectedRequest.documents.pco!.filename}
                              </p>
                              <div className="flex gap-2">
                                <button
                                  onClick={() => setImagePreview({ open: true, url: dataUrl, title: trans.pcoLicence || "PCO Licence" })}
                                  className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded text-xs font-semibold transition-colors"
                                >
                                  <FaEye />
                                  {trans.view || "View"}
                                </button>
                                <a 
                                  href={dataUrl}
                                  download={selectedRequest.documents.pco!.filename}
                                  className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white rounded text-xs font-semibold transition-colors"
                                >
                                  <FaDownload />
                                  {trans.download || "Download"}
                                </a>
                              </div>
                            </div>
                          );
                        })()}

                        {/* DBS Certificate */}
                        {selectedRequest.documents.dbs && (() => {
                          const mimeType = selectedRequest.documents.dbs!.extension.toLowerCase().includes('png') ? 'image/png' : 
                                          selectedRequest.documents.dbs!.extension.toLowerCase().includes('jpg') || 
                                          selectedRequest.documents.dbs!.extension.toLowerCase().includes('jpeg') ? 'image/jpeg' : 
                                          'application/octet-stream';
                          const dataUrl = `data:${mimeType};base64,${selectedRequest.documents.dbs!.content}`;
                          
                          return (
                            <div className="bg-card p-3 rounded-lg border border-border">
                              <div className="flex items-start justify-between mb-2">
                                <p className="text-xs md:text-sm font-medium text-muted-foreground">{trans.dbsCertificate || "DBS Certificate"}</p>
                                <span className="text-xs text-green-600 font-semibold">{(selectedRequest.documents.dbs!.size / 1024).toFixed(1)} KB</span>
                              </div>
                            <p className="text-[11px] text-muted-foreground/80 mb-2">
                              {trans.dbsCertificateDesc ||
                                "Disclosure and Barring Service certificate confirming the driver's background check."}
                            </p>
                              <p className="text-xs text-foreground mb-3 truncate" title={selectedRequest.documents.dbs!.filename}>
                                {selectedRequest.documents.dbs!.filename}
                              </p>
                              <div className="flex gap-2">
                                <button
                                  onClick={() => setImagePreview({ open: true, url: dataUrl, title: trans.dbsCertificate || "DBS Certificate" })}
                                  className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded text-xs font-semibold transition-colors"
                                >
                                  <FaEye />
                                  {trans.view || "View"}
                                </button>
                                <a 
                                  href={dataUrl}
                                  download={selectedRequest.documents.dbs!.filename}
                                  className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white rounded text-xs font-semibold transition-colors"
                                >
                                  <FaDownload />
                                  {trans.download || "Download"}
                                </a>
                              </div>
                            </div>
                          );
                        })()}

                        {/* DVLA Driving Licence */}
                        {selectedRequest.documents.dvla && (() => {
                          const mimeType = selectedRequest.documents.dvla!.extension.toLowerCase().includes('png') ? 'image/png' : 
                                          selectedRequest.documents.dvla!.extension.toLowerCase().includes('jpg') || 
                                          selectedRequest.documents.dvla!.extension.toLowerCase().includes('jpeg') ? 'image/jpeg' : 
                                          'application/octet-stream';
                          const dataUrl = `data:${mimeType};base64,${selectedRequest.documents.dvla!.content}`;
                          
                          return (
                            <div className="bg-card p-3 rounded-lg border border-border">
                              <div className="flex items-start justify-between mb-2">
                                <p className="text-xs md:text-sm font-medium text-muted-foreground">{trans.dvlaLicence || "DVLA Driving Licence"}</p>
                                <span className="text-xs text-green-600 font-semibold">{(selectedRequest.documents.dvla!.size / 1024).toFixed(1)} KB</span>
                              </div>
                            <p className="text-[11px] text-muted-foreground/80 mb-2">
                              {trans.dvlaLicenceDesc || "Copy of the driver's DVLA driving licence."}
                            </p>
                              <p className="text-xs text-foreground mb-3 truncate" title={selectedRequest.documents.dvla!.filename}>
                                {selectedRequest.documents.dvla!.filename}
                              </p>
                              <div className="flex gap-2">
                                <button
                                  onClick={() => setImagePreview({ open: true, url: dataUrl, title: trans.dvlaLicence || "DVLA Driving Licence" })}
                                  className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded text-xs font-semibold transition-colors"
                                >
                                  <FaEye />
                                  {trans.view || "View"}
                                </button>
                                <a 
                                  href={dataUrl}
                                  download={selectedRequest.documents.dvla!.filename}
                                  className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white rounded text-xs font-semibold transition-colors"
                                >
                                  <FaDownload />
                                  {trans.download || "Download"}
                                </a>
                              </div>
                            </div>
                          );
                        })()}
                      </div>
                    </div>

                    {/* Bank Details */}
                    {selectedRequest.documents.bank_details && (
                      <div>
                        <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                          </svg>
                          {trans.bankDetails || "Bank Details"}
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          <div className="bg-card p-3 rounded-lg border border-border">
                            <p className="text-xs font-medium text-muted-foreground mb-1">{trans.accountNumber || "Account Number"}</p>
                            <p className="text-sm font-bold text-foreground">{selectedRequest.documents.bank_details.bank_account_number}</p>
                          </div>
                          <div className="bg-card p-3 rounded-lg border border-border">
                            <p className="text-xs font-medium text-muted-foreground mb-1">{trans.sortCode || "Sort Code"}</p>
                            <p className="text-sm font-bold text-foreground">{selectedRequest.documents.bank_details.sort_code}</p>
                          </div>
                          <div className="bg-card p-3 rounded-lg border border-border md:col-span-1">
                            <p className="text-xs font-medium text-muted-foreground mb-1">{trans.registeredAddress || "Registered Address"}</p>
                            <p className="text-sm font-bold text-foreground">{selectedRequest.documents.bank_details.registered_address}</p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Vehicle Documents */}
                    {selectedRequest.documents.vehicle && (
                      <div>
                        <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                          </svg>
                          {trans.vehicleDocuments || "Vehicle Documents"}
                        </h4>
                        
                        {/* Vehicle Info */}
                        <div className="grid grid-cols-2 gap-3 mb-4">
                          <div className="bg-card p-3 rounded-lg border border-border">
                            <p className="text-xs font-medium text-muted-foreground mb-1">{trans.vehicleNumber || "Vehicle Number"}</p>
                            <p className="text-sm font-bold text-foreground">{selectedRequest.documents.vehicle.vehicle_number}</p>
                          </div>
                          <div className="bg-card p-3 rounded-lg border border-border">
                            <p className="text-xs font-medium text-muted-foreground mb-1">{trans.yearOfManufacture || "Year of Manufacture"}</p>
                            <p className="text-sm font-bold text-foreground">{selectedRequest.documents.vehicle.year_of_manufacture}</p>
                          </div>
                        </div>

                        {/* Vehicle Document Files */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {/* MOT Certificate */}
                          {selectedRequest.documents.vehicle.mot && (() => {
                            const mimeType = selectedRequest.documents.vehicle.mot!.extension.toLowerCase().includes('png') ? 'image/png' : 
                                            selectedRequest.documents.vehicle.mot!.extension.toLowerCase().includes('jpg') || 
                                            selectedRequest.documents.vehicle.mot!.extension.toLowerCase().includes('jpeg') ? 'image/jpeg' : 
                                            'application/octet-stream';
                            const dataUrl = `data:${mimeType};base64,${selectedRequest.documents.vehicle.mot!.content}`;
                            
                            return (
                              <div className="bg-card p-3 rounded-lg border border-border">
                                <div className="flex items-start justify-between mb-2">
                                  <p className="text-xs md:text-sm font-medium text-muted-foreground">{trans.motCertificate || "MOT Certificate"}</p>
                                  <span className="text-xs text-green-600 font-semibold">{(selectedRequest.documents.vehicle.mot!.size / 1024).toFixed(1)} KB</span>
                                </div>
                                <p className="text-[11px] text-muted-foreground/80 mb-2">
                                  {trans.motCertificateDesc ||
                                    "Latest MOT certificate confirming the vehicle passed its safety inspection."}
                                </p>
                                <p className="text-xs text-foreground mb-3 truncate" title={selectedRequest.documents.vehicle.mot!.filename}>
                                  {selectedRequest.documents.vehicle.mot!.filename}
                                </p>
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => setImagePreview({ open: true, url: dataUrl, title: trans.motCertificate || "MOT Certificate" })}
                                    className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded text-xs font-semibold transition-colors"
                                  >
                                    <FaEye />
                                    {trans.view || "View"}
                                  </button>
                                  <a 
                                    href={dataUrl}
                                    download={selectedRequest.documents.vehicle.mot!.filename}
                                    className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white rounded text-xs font-semibold transition-colors"
                                  >
                                    <FaDownload />
                                    {trans.download || "Download"}
                                  </a>
                                </div>
                              </div>
                            );
                          })()}

                          {/* PHV Licence */}
                          {selectedRequest.documents.vehicle.phv && (() => {
                            const mimeType = selectedRequest.documents.vehicle.phv!.extension.toLowerCase().includes('png') ? 'image/png' : 
                                            selectedRequest.documents.vehicle.phv!.extension.toLowerCase().includes('jpg') || 
                                            selectedRequest.documents.vehicle.phv!.extension.toLowerCase().includes('jpeg') ? 'image/jpeg' : 
                                            'application/octet-stream';
                            const dataUrl = `data:${mimeType};base64,${selectedRequest.documents.vehicle.phv!.content}`;
                            
                            return (
                              <div className="bg-card p-3 rounded-lg border border-border">
                                <div className="flex items-start justify-between mb-2">
                                  <p className="text-xs md:text-sm font-medium text-muted-foreground">{trans.phvLicence || "PHV Licence"}</p>
                                  <span className="text-xs text-green-600 font-semibold">{(selectedRequest.documents.vehicle.phv!.size / 1024).toFixed(1)} KB</span>
                                </div>
                                <p className="text-[11px] text-muted-foreground/80 mb-2">
                                  {trans.phvLicenceDesc ||
                                    "Private Hire Vehicle (PHV) licence for the vehicle registered with TfL."}
                                </p>
                                <p className="text-xs text-foreground mb-3 truncate" title={selectedRequest.documents.vehicle.phv!.filename}>
                                  {selectedRequest.documents.vehicle.phv!.filename}
                                </p>
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => setImagePreview({ open: true, url: dataUrl, title: trans.phvLicence || "PHV Licence" })}
                                    className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded text-xs font-semibold transition-colors"
                                  >
                                    <FaEye />
                                    {trans.view || "View"}
                                  </button>
                                  <a 
                                    href={dataUrl}
                                    download={selectedRequest.documents.vehicle.phv!.filename}
                                    className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white rounded text-xs font-semibold transition-colors"
                                  >
                                    <FaDownload />
                                    {trans.download || "Download"}
                                  </a>
                                </div>
                              </div>
                            );
                          })()}

                          {/* Vehicle Insurance */}
                          {selectedRequest.documents.vehicle.insurance && (() => {
                            const mimeType = selectedRequest.documents.vehicle.insurance!.extension.toLowerCase().includes('png') ? 'image/png' : 
                                            selectedRequest.documents.vehicle.insurance!.extension.toLowerCase().includes('jpg') || 
                                            selectedRequest.documents.vehicle.insurance!.extension.toLowerCase().includes('jpeg') ? 'image/jpeg' : 
                                            'application/octet-stream';
                            const dataUrl = `data:${mimeType};base64,${selectedRequest.documents.vehicle.insurance!.content}`;
                            
                            return (
                              <div className="bg-card p-3 rounded-lg border border-border">
                                <div className="flex items-start justify-between mb-2">
                                  <p className="text-xs md:text-sm font-medium text-muted-foreground">{trans.vehicleInsurance || "Vehicle Insurance"}</p>
                                  <span className="text-xs text-green-600 font-semibold">{(selectedRequest.documents.vehicle.insurance!.size / 1024).toFixed(1)} KB</span>
                                </div>
                                <p className="text-[11px] text-muted-foreground/80 mb-2">
                                  {trans.vehicleInsuranceDesc ||
                                    "Valid insurance policy covering the vehicle for private hire work."}
                                </p>
                                <p className="text-xs text-foreground mb-3 truncate" title={selectedRequest.documents.vehicle.insurance!.filename}>
                                  {selectedRequest.documents.vehicle.insurance!.filename}
                                </p>
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => setImagePreview({ open: true, url: dataUrl, title: trans.vehicleInsurance || "Vehicle Insurance" })}
                                    className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded text-xs font-semibold transition-colors"
                                  >
                                    <FaEye />
                                    {trans.view || "View"}
                                  </button>
                                  <a 
                                    href={dataUrl}
                                    download={selectedRequest.documents.vehicle.insurance!.filename}
                                    className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white rounded text-xs font-semibold transition-colors"
                                  >
                                    <FaDownload />
                                    {trans.download || "Download"}
                                  </a>
                                </div>
                              </div>
                            );
                          })()}
                        </div>
                      </div>
                    )}
                  </div>
                  ) : (
                    <div className="bg-card p-4 rounded-lg border border-border text-center">
                      <p className="text-sm text-muted-foreground">
                        {trans.noDocuments || "No documents uploaded yet"}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Admin Notes / Rejection Reason */}
              {(selectedRequest.admin_notes || selectedRequest.rejection_reason) && (
                <div className="bg-muted border-2 border-amber-400/50 rounded-xl p-4 md:p-5">
                  <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                    <span className="w-1 h-6 bg-amber-500 rounded-full"></span>
                    {trans.adminInfo || "Admin Information"}
                  </h3>
                  <div className="space-y-3">
                    {selectedRequest.admin_notes && (
                      <div className="bg-card p-3 rounded-lg border border-border">
                        <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">{trans.adminNotes || "Admin Notes"}</p>
                        <p className="font-semibold text-foreground text-sm md:text-base">{selectedRequest.admin_notes}</p>
                      </div>
                    )}
                    {selectedRequest.rejection_reason && (
                      <div className="bg-card p-3 rounded-lg border border-border">
                        <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                          {trans.rejectionReason || "Rejection Reason"}
                        </p>
                        <p className="font-semibold text-red-600 text-sm md:text-base">{selectedRequest.rejection_reason}</p>
                      </div>
                    )}
                    {selectedRequest.reviewed_at && (
                      <div className="bg-card p-3 rounded-lg border border-border">
                        <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">{trans.reviewedAt || "Reviewed At"}</p>
                        <p className="font-semibold text-foreground text-sm md:text-base">
                          {formatDate(new Date(selectedRequest.reviewed_at), locale)}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="sticky bottom-0 bg-gradient-to-t from-card to-background px-4 md:px-6 py-4 md:py-5 border-t-2 border-border rounded-b-2xl">
              <div className="flex flex-col sm:flex-row items-center gap-3">
                {/* Initial Review Actions (for pending status) */}
                {selectedRequest?.status === "pending" && (
                  <>
                    <Button
                      onClick={() =>
                        setActionModal({
                          open: true,
                          type: "approve",
                          requestId: selectedRequest?.id || null,
                          isFinalReview: false,
                        })
                      }
                      className="w-full sm:flex-1 bg-green-500 hover:bg-green-600 text-white font-semibold shadow-lg shadow-green-500/20"
                    >
                      <FaCheckCircle className="mr-2" />
                      {trans.approve || "Approve"}
                    </Button>
                    <Button
                      onClick={() =>
                        setActionModal({
                          open: true,
                          type: "reject",
                          requestId: selectedRequest?.id || null,
                          isFinalReview: false,
                        })
                      }
                      className="w-full sm:flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold shadow-lg shadow-red-500/20"
                    >
                      <FaTimesCircle className="mr-2" />
                      {trans.reject || "Reject"}
                    </Button>
                  </>
                )}
                
                {/* Final Review Actions (for documents_uploaded status) */}
                {selectedRequest?.status === "documents_uploaded" && (
                  <>
                    <Button
                      onClick={() =>
                        setActionModal({
                          open: true,
                          type: "approve",
                          requestId: selectedRequest?.id || null,
                          isFinalReview: true,
                        })
                      }
                      className="w-full sm:flex-1 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold shadow-lg shadow-emerald-500/20"
                    >
                      <FaCheckCircle className="mr-2" />
                      {trans.finalApprove || "Final Approve"}
                    </Button>
                    <Button
                      onClick={() =>
                        setActionModal({
                          open: true,
                          type: "modify",
                          requestId: selectedRequest?.id || null,
                          isFinalReview: true,
                        })
                      }
                      className="w-full sm:flex-1 bg-orange-500 hover:bg-orange-600 text-white font-semibold shadow-lg shadow-orange-500/20"
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                      {trans.requestModification || "Request Modification"}
                    </Button>
                    <Button
                      onClick={() =>
                        setActionModal({
                          open: true,
                          type: "reject",
                          requestId: selectedRequest?.id || null,
                          isFinalReview: true,
                        })
                      }
                      className="w-full sm:flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold shadow-lg shadow-red-500/20"
                    >
                      <FaTimesCircle className="mr-2" />
                      {trans.finalReject || "Final Reject"}
                    </Button>
                  </>
                )}
                
                <Button
                  onClick={() => {
                    setOpenDetails(false);
                    setSelectedRequestId(null);
                  }}
                  variant="secondary"
                  className="w-full sm:flex-1 font-semibold bg-gray-600 hover:bg-gray-500 text-white"
                >
                  {trans.close || "Close"}
                </Button>
              </div>
            </div>
            </>
            ) : (
              <div className="p-4 md:p-6 text-center text-muted-foreground">
                {trans.noData || "No data available"}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action Confirmation Modal - Dark Theme */}
      <GlobalModal isOpen={actionModal.open} onClose={() => setActionModal({ open: false, type: null, requestId: null, isFinalReview: false })}>
        <div className="p-4 md:p-6 space-y-5 bg-card rounded-xl">
          <div className="text-center">
            <div className={`w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center ${
              actionModal.type === "approve" 
                ? actionModal.isFinalReview ? "bg-emerald-500/20" : "bg-green-500/20"
                : actionModal.type === "modify"
                ? "bg-orange-500/20"
                : "bg-red-500/20"
            }`}>
              {actionModal.type === "approve" ? (
                <FaCheckCircle className={actionModal.isFinalReview ? "text-emerald-500 text-3xl" : "text-green-500 text-3xl"} />
              ) : actionModal.type === "modify" ? (
                <svg className="w-10 h-10 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              ) : (
                <FaTimesCircle className="text-red-500 text-3xl" />
              )}
            </div>
            <h3 className="text-xl md:text-2xl font-bold text-foreground mb-2">
              {actionModal.type === "approve"
                ? actionModal.isFinalReview 
                  ? trans.finalApproveTitle || "Final Approve Request?"
                  : trans.approveTitle || "Approve Request?"
                : actionModal.type === "modify"
                ? trans.modifyTitle || "Request Modification?"
                : actionModal.isFinalReview
                ? trans.finalRejectTitle || "Final Reject Request?"
                : trans.rejectTitle || "Reject Request?"}
            </h3>
            <p className="text-sm md:text-base text-muted-foreground">
              {actionModal.type === "approve"
                ? actionModal.isFinalReview
                  ? trans.finalApproveDesc || "Are you sure you want to give final approval to this driver onboarding request?"
                  : trans.approveDesc || "Are you sure you want to approve this driver onboarding request?"
                : actionModal.type === "modify"
                ? trans.modifyDesc || "Request the driver to modify their documents or information?"
                : actionModal.isFinalReview
                ? trans.finalRejectDesc || "Are you sure you want to finally reject this driver onboarding request?"
                : trans.rejectDesc || "Are you sure you want to reject this driver onboarding request?"}
            </p>
          </div>

          {(actionModal.type === "reject" || actionModal.type === "modify") && (
            <div>
              <label className="text-sm md:text-base font-semibold text-foreground mb-2 block">
                {actionModal.type === "modify" 
                  ? trans.modificationReason || "Modification Reason"
                  : trans.rejectionReason || "Rejection Reason"} <span className="text-red-500">*</span>
              </label>
              <textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                className={`w-full p-3 md:p-4 border-2 bg-background border-border rounded-lg focus:outline-none ${
                  actionModal.type === "modify" 
                    ? "focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20"
                    : "focus:border-red-500 focus:ring-2 focus:ring-red-500/20"
                } min-h-[100px] text-foreground text-sm md:text-base placeholder:text-muted-foreground`}
                placeholder={
                  actionModal.type === "modify"
                    ? trans.modificationPlaceholder || "Please specify what needs to be modified..."
                    : trans.rejectionPlaceholder || "Please provide a reason for rejection..."
                }
              />
            </div>
          )}

          {/* Files to Modify - Only for modify action in final review */}
          {actionModal.type === "modify" && actionModal.isFinalReview && selectedRequest && (
            <div>
              <label className="text-sm md:text-base font-semibold text-foreground mb-3 block">
                {trans.filesToModify || "Files to Modify"} <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 bg-muted rounded-lg border-2 border-border">
                {/* Driver Documents */}
                {selectedRequest.documents?.pco && (
                  <label className="flex items-center gap-3 p-3 bg-card rounded-lg border border-border cursor-pointer hover:bg-muted transition-colors">
                    <input
                      type="checkbox"
                      checked={filesToModify.includes("pco")}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFilesToModify([...filesToModify, "pco"]);
                        } else {
                          setFilesToModify(filesToModify.filter(f => f !== "pco"));
                        }
                      }}
                      className="w-5 h-5 text-orange-500 border-border rounded focus:ring-2 focus:ring-orange-500/20"
                    />
                    <span className="text-sm md:text-base font-semibold text-foreground">
                      {trans.pcoLicence || "PCO Licence"}
                    </span>
                  </label>
                )}
                {selectedRequest.documents?.dbs && (
                  <label className="flex items-center gap-3 p-3 bg-card rounded-lg border border-border cursor-pointer hover:bg-muted transition-colors">
                    <input
                      type="checkbox"
                      checked={filesToModify.includes("dbs")}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFilesToModify([...filesToModify, "dbs"]);
                        } else {
                          setFilesToModify(filesToModify.filter(f => f !== "dbs"));
                        }
                      }}
                      className="w-5 h-5 text-orange-500 border-border rounded focus:ring-2 focus:ring-orange-500/20"
                    />
                    <span className="text-sm md:text-base font-semibold text-foreground">
                      {trans.dbsCertificate || "DBS Certificate"}
                    </span>
                  </label>
                )}
                {selectedRequest.documents?.dvla && (
                  <label className="flex items-center gap-3 p-3 bg-card rounded-lg border border-border cursor-pointer hover:bg-muted transition-colors">
                    <input
                      type="checkbox"
                      checked={filesToModify.includes("dvla")}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFilesToModify([...filesToModify, "dvla"]);
                        } else {
                          setFilesToModify(filesToModify.filter(f => f !== "dvla"));
                        }
                      }}
                      className="w-5 h-5 text-orange-500 border-border rounded focus:ring-2 focus:ring-orange-500/20"
                    />
                    <span className="text-sm md:text-base font-semibold text-foreground">
                      {trans.dvlaLicence || "DVLA Driving Licence"}
                    </span>
                  </label>
                )}
                {/* Vehicle Documents */}
                {selectedRequest.documents?.vehicle?.mot && (
                  <label className="flex items-center gap-3 p-3 bg-card rounded-lg border border-border cursor-pointer hover:bg-muted transition-colors">
                    <input
                      type="checkbox"
                      checked={filesToModify.includes("mot")}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFilesToModify([...filesToModify, "mot"]);
                        } else {
                          setFilesToModify(filesToModify.filter(f => f !== "mot"));
                        }
                      }}
                      className="w-5 h-5 text-orange-500 border-border rounded focus:ring-2 focus:ring-orange-500/20"
                    />
                    <span className="text-sm md:text-base font-semibold text-foreground">
                      {trans.motCertificate || "MOT Certificate"}
                    </span>
                  </label>
                )}
                {selectedRequest.documents?.vehicle?.phv && (
                  <label className="flex items-center gap-3 p-3 bg-card rounded-lg border border-border cursor-pointer hover:bg-muted transition-colors">
                    <input
                      type="checkbox"
                      checked={filesToModify.includes("phv")}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFilesToModify([...filesToModify, "phv"]);
                        } else {
                          setFilesToModify(filesToModify.filter(f => f !== "phv"));
                        }
                      }}
                      className="w-5 h-5 text-orange-500 border-border rounded focus:ring-2 focus:ring-orange-500/20"
                    />
                    <span className="text-sm md:text-base font-semibold text-foreground">
                      {trans.phvLicence || "PHV Licence"}
                    </span>
                  </label>
                )}
                {selectedRequest.documents?.vehicle?.insurance && (
                  <label className="flex items-center gap-3 p-3 bg-card rounded-lg border border-border cursor-pointer hover:bg-muted transition-colors">
                    <input
                      type="checkbox"
                      checked={filesToModify.includes("insurance")}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFilesToModify([...filesToModify, "insurance"]);
                        } else {
                          setFilesToModify(filesToModify.filter(f => f !== "insurance"));
                        }
                      }}
                      className="w-5 h-5 text-orange-500 border-border rounded focus:ring-2 focus:ring-orange-500/20"
                    />
                    <span className="text-sm md:text-base font-semibold text-foreground">
                      {trans.vehicleInsurance || "Vehicle Insurance"}
                    </span>
                  </label>
                )}
              </div>
              {filesToModify.length === 0 && (
                <p className="text-xs text-red-500 mt-2">
                  {trans.selectAtLeastOneFile || "Please select at least one file that needs modification"}
                </p>
              )}
            </div>
          )}

          <div>
            <label className="text-sm md:text-base font-semibold text-foreground mb-2 block">
              {trans.adminNotes || "Admin Notes"} <span className="text-muted-foreground font-normal">{trans.optional || "(Optional)"}</span>
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full p-3 md:p-4 border-2 bg-background border-border rounded-lg focus:outline-none focus:border-yellow-500 focus:ring-2 focus:ring-yellow-500/20 min-h-[80px] text-foreground text-sm md:text-base placeholder:text-muted-foreground"
              placeholder={trans.notesPlaceholder || "Add any additional notes..."}
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <Button
              onClick={handleAction}
              disabled={actionMutation.isPending}
              className={`w-full sm:flex-1 font-semibold ${
                actionModal.type === "approve"
                  ? actionModal.isFinalReview
                    ? "bg-emerald-500 hover:bg-emerald-600 text-white shadow-lg shadow-emerald-500/20"
                    : "bg-green-500 hover:bg-green-600 text-white shadow-lg shadow-green-500/20"
                  : actionModal.type === "modify"
                  ? "bg-orange-500 hover:bg-orange-600 text-white shadow-lg shadow-orange-500/20"
                  : "bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/20"
              }`}
            >
              {actionMutation.isPending
                ? trans.processing || "Processing..."
                : actionModal.type === "approve"
                ? actionModal.isFinalReview
                  ? trans.confirmFinalApprove || "Confirm Final Approve"
                  : trans.confirmApprove || "Confirm Approve"
                : actionModal.type === "modify"
                ? trans.confirmModify || "Confirm Request Modification"
                : actionModal.isFinalReview
                ? trans.confirmFinalReject || "Confirm Final Reject"
                : trans.confirmReject || "Confirm Reject"}
            </Button>
            <Button
              onClick={() => {
                setActionModal({ open: false, type: null, requestId: null, isFinalReview: false });
                setNotes("");
                setRejectionReason("");
                setFilesToModify([]);
              }}
              variant="secondary"
              className="w-full sm:flex-1 font-semibold"
              disabled={actionMutation.isPending}
            >
              {trans.cancel || "Cancel"}
            </Button>
          </div>
        </div>
      </GlobalModal>

      {/* Image Preview Modal */}
      {imagePreview.open && (
        <div
          onClick={() => setImagePreview({ open: false, url: "", title: "" })}
          className="fixed inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center z-[60] p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-card rounded-2xl w-full max-w-5xl shadow-2xl max-h-[95vh] overflow-hidden border-2 border-border"
          >
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-card to-background px-4 md:px-6 py-4 border-b-2 border-border flex items-center justify-between">
              <h3 className="text-lg md:text-xl font-bold text-foreground">{imagePreview.title}</h3>
              <button
                onClick={() => setImagePreview({ open: false, url: "", title: "" })}
                className="p-2 hover:bg-muted rounded-lg transition-colors text-muted-foreground hover:text-foreground"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Image Container */}
            <div className="p-4 md:p-6 bg-muted flex items-center justify-center max-h-[calc(95vh-100px)] overflow-auto">
              <img 
                src={imagePreview.url} 
                alt={imagePreview.title}
                className="max-w-full max-h-full object-contain rounded-lg shadow-xl"
              />
            </div>

            {/* Modal Footer */}
            <div className="bg-gradient-to-t from-card to-background px-4 md:px-6 py-4 border-t-2 border-border flex gap-3">
              <a
                href={imagePreview.url}
                download={imagePreview.title}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-semibold transition-colors"
              >
                <FaDownload />
                {trans.download || "Download"}
              </a>
              <Button
                onClick={() => setImagePreview({ open: false, url: "", title: "" })}
                variant="secondary"
                className="flex-1 font-semibold"
              >
                {trans.close || "Close"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}


 