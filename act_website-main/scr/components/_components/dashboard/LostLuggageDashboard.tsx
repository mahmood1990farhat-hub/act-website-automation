"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Locale } from "../../../../i18n.config";
import { fetchData } from "@/lib/api/fetchData";
import IsLoading from "../ISloading";
import Pagination from "../Pagination";
import { FaBox, FaDownload, FaEdit, FaTimes } from "react-icons/fa";
import { toast } from "react-toastify";
import {
  LostPropertyContactPreferences,
  LostPropertyItemTypes,
  LostPropertyStatus,
} from "@/constants/enums";
import GlobalModal from "../GlobalModal";
import { HiOutlineEye, HiOutlineX } from "react-icons/hi";
import { Button } from "@/components/ui/button";
import { extract_error } from "@/lib/api/errorApi";

type LostLuggageDashboardProps = {
  trans: any;
  token?: string;
  locale: Locale;
};

export default function LostLuggageDashboard({
  trans,
  token,
  locale,
}: LostLuggageDashboardProps) {
  const [page, setPage] = useState(1);
  const [filterStatus, setFilterStatus] = useState<"" | LostPropertyStatus>("");
  const [filterItemType, setFilterItemType] =
    useState<"" | LostPropertyItemTypes>("");

  const [selectedReport, setSelectedReport] = useState<any | null>(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [selectedImage, setSelectedImage] = useState<{ url: string; reportId: number } | null>(null);
  const [updateForm, setUpdateForm] = useState<{
    status: "" | LostPropertyStatus;
    admin_notes: string;
  }>({ status: "" as "" | LostPropertyStatus, admin_notes: "" });

  const queryClient = useQueryClient();

  const {
    data: reportsData,
    isLoading: reportsLoading,
  } = useQuery<any>({
    queryKey: ["admin-lost-property", page, filterStatus, filterItemType],
    queryFn: () =>
      fetchData({
        endpoint: "/api/admin-panel/lost-property/",
        token: token,
        queryParams: {
          locale,
          page: page.toString(),
          page_size: "10",
          ...(filterStatus && { status: filterStatus }),
          ...(filterItemType && { item_type: filterItemType }),
        },
      }),
  });

  // Normalise API response shape:
  // - Passenger lost property uses { data: { lost_property_reports, stats, pagination } }
  // - Admin lost property (your current API) uses { success, data: [..], pagination: {...} }
  const raw = reportsData || {};
  let reports: any[] = [];
  let stats: any = {};
  let pagination: any = raw.pagination || {};

  if (raw.data) {
    if (Array.isArray(raw.data)) {
      // Shape: { success, data: [ ... ], pagination: {...} }
      reports = raw.data;
    } else if (typeof raw.data === "object") {
      // Shape: { data: { lost_property_reports, stats, pagination } }
      if (Array.isArray(raw.data.lost_property_reports)) {
        reports = raw.data.lost_property_reports;
      } else if (Array.isArray(raw.data.data)) {
        // Fallback: sometimes nested "data" array
        reports = raw.data.data;
      }
      stats = raw.data.stats || {};
      pagination = raw.data.pagination || pagination;
    }
  } else if (Array.isArray(raw.lost_property_reports)) {
    // Direct array on root (defensive)
    reports = raw.lost_property_reports;
  }

  const statusOptions = Object.values(LostPropertyStatus);
  const itemTypeOptions = Object.values(LostPropertyItemTypes);

  const humanize = (value: string) =>
    value
      .replace(/_/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .replace(/\b\w/g, (char) => char.toUpperCase());

  const getItemTypeLabel = (value: string) =>
    trans?.report_list?.item_types?.[
      value as keyof typeof trans.report_list.item_types
    ] ?? humanize(value);

  const getStatusLabel = (value: string) => {
    if (Array.isArray(trans?.status)) {
      const match = trans.status.find((s: any) => s.value === value);
      if (match?.title) return match.title;
    }
    return (
      trans?.statuses?.[value as keyof typeof trans.statuses] ?? humanize(value)
    );
  };

  const getContactLabel = (value: string) =>
    trans?.submit_form?.fields?.contact_options?.[
      value as keyof typeof trans.submit_form.fields.contact_options
    ] ??
    trans?.contact_preferences?.[
      value as keyof typeof trans.contact_preferences
    ] ??
    humanize(value);

  // Helper function to get photo URL from API response
  const getPhotoUrl = (photo: string | { content?: string; extension?: string } | null | undefined): string => {
    if (!photo) return '';
    if (typeof photo === 'string') return photo;
    if (typeof photo === 'object' && photo !== null && 'content' in photo && photo.content) {
      const extension = photo.extension?.replace('.', '') || 'png';
      return `data:image/${extension};base64,${photo.content}`;
    }
    return '';
  };

  const getStatusColor = (status: LostPropertyStatus | string) => {
    switch (status) {
      case LostPropertyStatus.REPORTED:
        return "bg-blue-50 text-blue-700 border-blue-200";
      case LostPropertyStatus.UNDER_INVESTIGATION:
        return "bg-yellow-50 text-yellow-700 border-yellow-200";
      case LostPropertyStatus.FOUND:
        return "bg-green-50 text-green-700 border-green-200";
      case LostPropertyStatus.RETURNED:
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case LostPropertyStatus.NOT_FOUND:
        return "bg-red-50 text-red-700 border-red-200";
      case LostPropertyStatus.CLOSED:
        return "bg-gray-100 text-gray-700 border-gray-200";
      default:
        return "bg-gray-100 text-gray-700 border-gray-200";
    }
  };

  const updateMutation = useMutation({
    mutationFn: async ({
      id,
      status,
      admin_notes,
    }: {
      id: number;
      status: LostPropertyStatus | "";
      admin_notes: string;
    }) => {
      if (!token) {
        throw new Error("Missing admin token");
      }
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/admin-panel/lost-property/${id}/respond/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            status: status || undefined,
            admin_notes: admin_notes || undefined,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = extract_error(errorData);
        throw new Error(errorMessage);
      }

      return response.json();
    },
    onSuccess: () => {
      toast.success("Report updated successfully");
      queryClient.invalidateQueries({ queryKey: ["admin-lost-property"] });
      setSelectedReport(null);
    },
    onError: (error: any) => {
      const errorMessage = extract_error(error) || error?.message || "Failed to update report";
      toast.error(errorMessage);
    },
  });

  const openUpdateModal = (report: any) => {
    setSelectedReport(report);
    setUpdateForm({
      status: (report.status || "") as "" | LostPropertyStatus,
      admin_notes: report.admin_notes || "",
    });
  };

  const handleUpdateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedReport) return;
    updateMutation.mutate({
      id: selectedReport.id,
      status: updateForm.status,
      admin_notes: updateForm.admin_notes,
    });
  };

  const handleDownload = async (id: number) => {
    try {
      const base =
        process.env.NEXT_PUBLIC_API_BASE_URL || window.location.origin;
      const url = `${base}/api/admin-panel/lost-property/${id}/download-pdf/`;

      const response = await fetch(url, {
        method: "GET",
        headers: token
          ? {
              Authorization: `Bearer ${token}`,
            }
          : undefined,
      });

      if (!response.ok) {
        throw new Error("Failed to download PDF");
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `lost-property-report-${id}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err: any) {
      console.error(err);
      const errorMessage = extract_error(err) || err?.message || "Failed to download PDF";
      toast.error(errorMessage);
    }
  };

  const handleDownloadImage = (imageUrl: string, reportId: number) => {
    try {
      // Determine file extension from the image URL
      let extension = 'png';
      if (imageUrl.includes('data:image/')) {
        const mimeMatch = imageUrl.match(/data:image\/([^;]+)/);
        if (mimeMatch) {
          extension = mimeMatch[1] === 'jpeg' ? 'jpg' : mimeMatch[1];
        }
      } else if (imageUrl.includes('.')) {
        const urlMatch = imageUrl.match(/\.([a-zA-Z0-9]+)(?:[?#]|$)/);
        if (urlMatch) {
          extension = urlMatch[1];
        }
      }

      // Create a temporary anchor element
      const link = document.createElement("a");
      link.href = imageUrl;
      link.download = `lost-property-${reportId}-photo.${extension}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast.success("Image downloaded successfully");
    } catch (error) {
      toast.error("Failed to download image");
    }
  };

  return (
    <div className="w-full">
      {/* Header with Stats */}
      <div className="mb-8">
       

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
          {Object.entries(stats).map(([key, value]: [string, any]) => (
            <div
              key={key}
              className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm"
            >
              <p className="text-gray-500 text-xs mb-1">
                {trans.stats[key] ?? humanize(key)}
              </p>
              <p className="text-gray-900 text-xl font-bold">{value}</p>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl p-4 mb-6 border border-gray-200 shadow-sm">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Status Filter */}
            <div>
              <label className="block mb-2 text-[16px] text-gray-800">
                {trans.report_list.filter.status_label}
              </label>
              <select
                value={filterStatus}
                onChange={(e) => {
                  setFilterStatus(e.target.value as "" | LostPropertyStatus);
                  setPage(1);
                }}
                className="w-full p-3 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="">
                  {trans.report_list.filter.all}
                </option>
                {statusOptions.map((status) => (
                  <option key={status} value={status}>
                    {getStatusLabel(status)}
                  </option>
                ))}
              </select>
            </div>

            {/* Item Type Filter */}
            <div>
              <label className="block mb-2 text-[16px] text-gray-800">
                {trans.report_list.filter.item_type_label}
              </label>
              <select
                value={filterItemType}
                onChange={(e) => {
                  setFilterItemType(
                    e.target.value as "" | LostPropertyItemTypes
                  );
                  setPage(1);
                }}
                className="w-full p-3 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="">
                  {trans.report_list.item_types.all}
                </option>
                {itemTypeOptions.map((type) => (
                  <option key={type} value={type}>
                    {getItemTypeLabel(type)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Reports List */}
      {reportsLoading ? (
        <div className="flex items-center justify-center py-20">
          <IsLoading />
        </div>
      ) : reports.length === 0 ? (
        <div className="bg-white rounded-xl p-12 border border-gray-200 text-center shadow-sm">
          <FaBox className="text-gray-400 text-5xl mx-auto mb-4" />
          <p className="text-gray-500 text-lg">{trans.report_list.empty}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((report: any) => (
            <div
              key={report.id}
              className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-200"
            >
              <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3 flex-wrap">
                    <span
                      className={`px-3 py-1 rounded-lg text-xs font-semibold border ${getStatusColor(
                        report.status
                      )}`}
                    >
                      {getStatusLabel(report.status) ||
                        report.status_display}
                    </span>
                    <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-primary/20 text-primary border border-primary/40">
                      {getItemTypeLabel(report.item_type) ||
                        report.item_type_display}
                    </span>
                    <span className="text-gray-500 text-sm">
                      {trans.report_card.report_id}: #{report.id}
                    </span>
                  </div>

                  <h3 className="text-gray-900 text-lg font-bold mb-2">
                    {getItemTypeLabel(report.item_type) ||
                      report.item_type_display}
                  </h3>

                  <p className="text-gray-600 mb-3">
                    {report.item_description}
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                    {report.item_color && (
                      <div>
                        <span className="text-gray-500">
                          {trans.report_card.color}:{" "}
                        </span>
                        <span className="text-gray-900">
                          {report.item_color}
                        </span>
                      </div>
                    )}
                    {report.item_brand && (
                      <div>
                        <span className="text-gray-500">
                          {trans.report_card.brand}:{" "}
                        </span>
                        <span className="text-gray-900">
                          {report.item_brand}
                        </span>
                      </div>
                    )}
                   
                    <div>
                      <span className="text-gray-500">
                        {trans.report_card.contact_preference}:{" "}
                      </span>
                      <span className="text-gray-900">
                        {getContactLabel(report.contact_preference) ||
                          report.contact_preference_display}
                      </span>
                    </div>
                  </div>

                  {report.admin_notes && (
                    <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-sm">
                      <p className="text-gray-500 mb-1">
                        {trans.report_card.admin_notes}:
                      </p>
                      <p className="text-gray-900">{report.admin_notes}</p>
                    </div>
                  )}

                  <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-gray-500">
                    {report.found_at && (
                      <span>
                        {trans.report_card.found_at}:{" "}
                        <span className="text-green-600">
                          {new Date(report.found_at).toLocaleDateString(
                            locale === "ar" ? "ar-EG" : "en-US"
                          )}
                        </span>
                      </span>
                    )}
                    {report.returned_at && (
                      <span>
                        {trans.report_card.returned_at}:{" "}
                        <span className="text-emerald-600">
                          {new Date(report.returned_at).toLocaleDateString(
                            locale === "ar" ? "ar-EG" : "en-US"
                          )}
                        </span>
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col items-stretch gap-2 text-sm min-w-[200px]">
                  {report.trip_data && (
                    <div className="mb-3 text-gray-600">
                      <span className="block font-semibold mb-1 text-gray-900">
                        {trans.report_card.trip_date}
                      </span>
                      <span>{report.trip_data.trip_date}</span>
                    </div>
                    
                  )}
                  
                  <div className="mb-3 text-gray-600">
                    <span className="block font-semibold mb-1 text-gray-900">
                      {trans.report_card.created_at}
                    </span>
                    <span>
                      {new Date(report.created_at).toLocaleDateString(
                        locale === "ar" ? "ar-EG" : "en-US"
                      )}
                    </span>
                  </div>
                  <div>
                      <span className="text-gray-500">
                        {trans.report_card.lost_location}:{" "}
                      </span>
                      <span className="text-gray-900">
                        {report.lost_location}
                      </span>
                    </div>

                
                </div>
              </div>
              <div className=" grid gap-4 sm:grid-cols-2 md:grid-cols-3">
              <Button
                    onClick={() => {
                      setSelectedReport(report);
                      setShowDetailsModal(true);
                    }}
                    variant="outline"
                    className="w-full bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-foreground font-bold shadow-lg shadow-yellow-500/20"
                    >
                    <HiOutlineEye className="w-4 h-4" />
                    <span>{trans.report_card.show_details || "Show Details"}</span>
                  </Button>

                  <Button
                onClick={() => {
                  setShowDetailsModal(false);
                  openUpdateModal(report);
                }}
                variant="secondary"
                className="flex items-center gap-2"
              >
                <FaEdit className="w-4 h-4" />
                {trans.report_card.update_status || "Update Status"}
              </Button>

                  <Button
                    onClick={() => handleDownload(report.id)}
                    className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-xs font-semibold transition-colors"
                  >
                    <FaDownload />
                    <span>{trans.report_card.downloadPdf || "Download PDF"}</span>
                  </Button>
              </div>
            </div>
          ))}

          {/* Pagination */}
          {pagination.num_pages > 1 && (
            <div className="mt-6">
              <Pagination
                currentPage={page}
                totalPages={pagination.num_pages}
                onPageChange={setPage}
                locale={locale}
              />
            </div>
          )}
        </div>
      )}

      {/* Details Modal - Driver Onboarding Pattern */}
      {showDetailsModal && selectedReport && (
        <div
          onClick={() => {
            setShowDetailsModal(false);
            setSelectedReport(null);
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
                  {trans.report_card.report_details || "Lost Property Report Details"}
                </h2>
                <div className="flex items-center gap-3">
                  <span
                    className={`px-4 py-2 rounded-full text-xs xl:text-sm font-bold border ${getStatusColor(
                      selectedReport.status
                    )}`}
                  >
                    {getStatusLabel(selectedReport.status) || selectedReport.status_display}
                  </span>
                  <button
                    onClick={() => {
                      setShowDetailsModal(false);
                      setSelectedReport(null);
                    }}
                    className="p-2 hover:bg-muted rounded-lg transition-colors text-muted-foreground hover:text-foreground"
                  >
                    <HiOutlineX className="w-6 h-6" />
                  </button>
                </div>
              </div>
            </div>

            {/* Modal Content */}
            <div className="p-4 md:p-6 space-y-5 md:space-y-6">
              {/* Report Information */}
              <div className="bg-muted border-2 border-yellow-500/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-yellow-500 rounded-full"></span>
                  {trans.report_card.report_info || "Report Information"}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.report_card.report_id}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base">
                      #{selectedReport.id}
                    </p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.report_card.item_type || "Item Type"}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base break-words">
                      {getItemTypeLabel(selectedReport.item_type) || selectedReport.item_type_display}
                    </p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border sm:col-span-2">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.report_card.created_at}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base">
                      {new Date(selectedReport.created_at).toLocaleDateString(
                        locale === "ar" ? "ar-EG" : "en-US",
                        {
                          year: "numeric",
                          month: "long",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        }
                      )}
                    </p>
                  </div>
                </div>
              </div>

              {/* Item Description */}
              <div className="bg-muted border-2 border-blue-400/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-blue-500 rounded-full"></span>
                  {trans.report_card.description || "Description"}
                </h3>
                <div className="bg-card p-3 rounded-lg border border-border">
                  <p className="text-foreground text-sm md:text-base break-words whitespace-pre-wrap">
                    {selectedReport.item_description}
                  </p>
                </div>
              </div>

              {/* Item Details */}
              <div className="bg-muted border-2 border-purple-400/50 rounded-xl p-4 md:p-5">
                <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <span className="w-1 h-6 bg-purple-500 rounded-full"></span>
                  {trans.report_card.item_details || "Item Details"}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {selectedReport.item_color && (
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.report_card.color}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-words">
                        {selectedReport.item_color}
                      </p>
                    </div>
                  )}
                  {selectedReport.item_brand && (
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.report_card.brand}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-words">
                        {selectedReport.item_brand}
                      </p>
                    </div>
                  )}
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.report_card.lost_location}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base break-words">
                      {selectedReport.lost_location}
                    </p>
                  </div>
                  <div className="bg-card p-3 rounded-lg border border-border">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                      {trans.report_card.contact_preference}
                    </p>
                    <p className="font-semibold text-foreground text-sm md:text-base break-words">
                      {getContactLabel(selectedReport.contact_preference) || selectedReport.contact_preference_display}
                    </p>
                  </div>
                </div>
                
                {/* Photo Display */}
                {selectedReport.photo && (
                  <div className="mt-4">
                    <p className="text-xs md:text-sm font-medium text-muted-foreground mb-2">
                      {trans.report_card.photo || "Photo"}
                    </p>
                    <div 
                      className="relative w-full max-w-md h-48 sm:h-64 rounded-lg overflow-hidden border-2 border-border cursor-pointer hover:border-primary/50 transition-all duration-300"
                      onClick={() => setSelectedImage({ url: getPhotoUrl(selectedReport.photo), reportId: selectedReport.id })}
                    >
                      <img
                        src={getPhotoUrl(selectedReport.photo)}
                        alt="Lost item photo"
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = 'none';
                        }}
                      />
                      <div className="absolute inset-0 bg-black/0 hover:bg-black/10 transition-all duration-300 flex items-center justify-center">
                        <span className="text-white opacity-0 hover:opacity-100 text-sm font-semibold">Click to view</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Reporter Info */}
              {selectedReport.reporter && (
                <div className="bg-muted border-2 border-emerald-400/50 rounded-xl p-4 md:p-5">
                  <h3 className="text-base md:text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                    <span className="w-1 h-6 bg-emerald-500 rounded-full"></span>
                    {trans.report_card.reporter_info || "Reporter Information"}
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.report_card.full_name || "Full Name"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-words">
                        {selectedReport.reporter.full_name}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.report_card.phone_number || "Phone Number"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-words">
                        {selectedReport.reporter.phone_number}
                      </p>
                    </div>
                    <div className="bg-card p-3 rounded-lg border border-border sm:col-span-2">
                      <p className="text-xs md:text-sm font-medium text-muted-foreground mb-1">
                        {trans.report_card.email || "Email"}
                      </p>
                      <p className="font-semibold text-foreground text-sm md:text-base break-all">
                        {selectedReport.reporter.email}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Trip Data */}
              {selectedReport.trip_data && (
                <div className="bg-purple-50 border border-purple-200 p-4 rounded-lg">
                  <h3 className="text-gray-900 text-lg font-bold mb-3">
                    {trans.report_card.trip_info || "Trip Information"}
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-gray-500 text-sm mb-1">
                        {trans.report_card.trip_id || "Trip ID"}
                      </p>
                      <p className="text-gray-900 font-semibold">
                        #{selectedReport.trip_data.id}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-sm mb-1">
                        {trans.report_card.trip_date}
                      </p>
                      <p className="text-gray-900 font-semibold">
                        {selectedReport.trip_data.trip_date}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-sm mb-1">
                        {trans.report_card.trip_time || "Trip Time"}
                      </p>
                      <p className="text-gray-900 font-semibold">
                        {selectedReport.trip_data.trip_time}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-sm mb-1">
                        {trans.report_card.distance || "Distance"}
                      </p>
                      <p className="text-gray-900 font-semibold">
                        {selectedReport.trip_data.distance_miles} miles
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-sm mb-1">
                        {trans.report_card.duration || "Expected Duration"}
                      </p>
                      <p className="text-gray-900 font-semibold">
                        {selectedReport.trip_data.expected_trip_duration_minutes} minutes
                      </p>
                    </div>
                  </div>

                  {/* Passenger Info */}
                  {selectedReport.trip_data.passenger_info && (
                    <div className="mt-4 pt-4 border-t border-purple-300">
                      <h4 className="text-gray-900 font-bold mb-2">
                        {trans.report_card.passenger_info || "Passenger Information"}
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div>
                          <p className="text-gray-500 text-sm mb-1">
                            {trans.report_card.name || "Name"}
                          </p>
                          <p className="text-gray-900 font-semibold">
                            {selectedReport.trip_data.passenger_info.first_name}{" "}
                            {selectedReport.trip_data.passenger_info.last_name}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500 text-sm mb-1">
                            {trans.report_card.phone_number || "Phone"}
                          </p>
                          <p className="text-gray-900 font-semibold">
                            {selectedReport.trip_data.passenger_info.phone_number}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Driver Info */}
                  {selectedReport.trip_data.driver_info && (
                    <div className="mt-4 pt-4 border-t border-purple-300">
                      <h4 className="text-gray-900 font-bold mb-2">
                        {trans.report_card.driver_info || "Driver Information"}
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div>
                          <p className="text-gray-500 text-sm mb-1">
                            {trans.report_card.name || "Name"}
                          </p>
                          <p className="text-gray-900 font-semibold">
                            {selectedReport.trip_data.driver_info.first_name}{" "}
                            {selectedReport.trip_data.driver_info.last_name}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500 text-sm mb-1">
                            {trans.report_card.phone_number || "Phone"}
                          </p>
                          <p className="text-gray-900 font-semibold">
                            {selectedReport.trip_data.driver_info.phone_number}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Admin Notes */}
              {selectedReport.admin_notes && (
                <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg">
                  <h3 className="text-gray-900 text-lg font-bold mb-2">
                    {trans.report_card.admin_notes}
                  </h3>
                  <p className="text-gray-700">{selectedReport.admin_notes}</p>
                </div>
              )}

              {/* Found/Returned Dates */}
              {(selectedReport.found_at || selectedReport.returned_at) && (
                <div className="bg-green-50 border border-green-200 p-4 rounded-lg">
                  {selectedReport.found_at && (
                    <div className="mb-2">
                      <p className="text-gray-500 text-sm mb-1">
                        {trans.report_card.found_at}
                      </p>
                      <p className="text-gray-900 font-semibold">
                        {new Date(selectedReport.found_at).toLocaleDateString(
                          locale === "ar" ? "ar-EG" : "en-US",
                          {
                            year: "numeric",
                            month: "long",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          }
                        )}
                      </p>
                    </div>
                  )}
                  {selectedReport.returned_at && (
                    <div>
                      <p className="text-gray-500 text-sm mb-1">
                        {trans.report_card.returned_at}
                      </p>
                      <p className="text-gray-900 font-semibold">
                        {new Date(selectedReport.returned_at).toLocaleDateString(
                          locale === "ar" ? "ar-EG" : "en-US",
                          {
                            year: "numeric",
                            month: "long",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          }
                        )}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <Button
                onClick={() => {
                  setShowDetailsModal(false);
                  openUpdateModal(selectedReport);
                }}
                variant="secondary"
                className="flex items-center gap-2"
              >
                <FaEdit className="w-4 h-4" />
                {trans.report_card.update_status || "Update Status"}
              </Button>
              <Button
                onClick={() => {
                  setShowDetailsModal(false);
                  setSelectedReport(null);
                }}
                variant="outline"
                className="border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                {trans.report_card.close || "Close"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Update Modal */}
      <GlobalModal
        isOpen={!!selectedReport && !showDetailsModal}
        onClose={() => {
          if (!updateMutation.isPending) {
            setSelectedReport(null);
          }
        }}
      >
        <form
          onSubmit={handleUpdateSubmit}
          className="bg-white p-6 rounded-xl max-w-lg w-full"
        >
          <h2 className="text-xl font-bold mb-4 text-gray-900">
            {trans.report_card.updateReportTitle || "Update Lost Property Report"} #{selectedReport?.id}
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block mb-2 text-sm text-gray-700">
                {trans.report_card.status}
              </label>
              <select
                value={updateForm.status}
                onChange={(e) =>
                  setUpdateForm((prev) => ({
                    ...prev,
                    status: e.target.value as "" | LostPropertyStatus,
                  }))
                }
                className="w-full p-3 border border-gray-300 bg-white rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="">{trans.report_list.filter.all}</option>
                {statusOptions.map((status) => (
                  <option key={status} value={status}>
                    {getStatusLabel(status)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block mb-2 text-sm text-gray-700">
                {trans.report_card.admin_notes}
              </label>
              <textarea
              required
                value={updateForm.admin_notes}
                onChange={(e) =>
                  setUpdateForm((prev) => ({
                    ...prev,
                    admin_notes: e.target.value,
                  }))
                }
                className="w-full p-3 border border-gray-300 bg-white rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/40 min-h-[100px]"
                placeholder="Add internal notes about this report..."
              />
            </div>
          </div>

          <div className="mt-6 flex items-center gap-3">
            <button
              type="button"
              onClick={() => setSelectedReport(null)}
              disabled={updateMutation.isPending}
              className="flex-1 border border-gray-300 text-gray-700 py-2.5 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="flex-1 bg-primary text-black font-semibold py-2.5 rounded-lg hover:bg-primary/90 disabled:opacity-60 transition-colors"
            >
              {updateMutation.isPending ? "Saving..." : "Save changes"}
            </button>
          </div>
        </form>
      </GlobalModal>

      {/* Image Preview Modal */}
      {selectedImage && (
        <div
          onClick={() => setSelectedImage(null)}
          className="fixed inset-0 bg-black/80 bg-opacity-80 flex items-center justify-center z-50 p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-lg p-6 max-w-5xl w-full max-h-[95vh] overflow-auto"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-gray-900 text-xl font-bold">
                {trans.report_card.photo || "Photo Preview"}
              </h3>
              <button
                onClick={() => setSelectedImage(null)}
                className="text-gray-400 hover:text-gray-600 transition-colors p-2 hover:bg-gray-100 rounded-full"
              >
                <FaTimes className="text-2xl" />
              </button>
            </div>
            <div className="relative w-full mb-4 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center min-h-[400px]">
              <img
                src={selectedImage.url}
                alt="Lost item photo preview"
                className="w-full h-auto max-h-[75vh] object-contain mx-auto"
              />
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  if (selectedImage) {
                    handleDownloadImage(selectedImage.url, selectedImage.reportId);
                  }
                }}
                className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-black font-bold py-3 px-6 rounded-lg transition-all duration-300"
              >
                <FaDownload />
                {trans.download || "Download"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


