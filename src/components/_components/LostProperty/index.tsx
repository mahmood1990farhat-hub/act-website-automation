"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchData } from "@/lib/api/fetchData";
import { Locale } from "../../../../i18n.config";
import IsLoading from "../ISloading";
import Pagination from "../Pagination";
import { FaBox, FaPlus, FaList, FaDownload, FaTimes } from "react-icons/fa";
import { toast } from "react-toastify";
import GlobalModal from "../GlobalModal";
import {
  LostPropertyContactPreferences,
  LostPropertyItemTypes,
  LostPropertyStatus,
} from "@/constants/enums";
import { extract_error } from "@/lib/api/errorApi";

type LostPropertyProps = {
  trans: any;
  token?: string;
  locale: Locale;
};

export default function LostProperty({ trans, token, locale }: LostPropertyProps) {
  const [activeTab, setActiveTab] = useState<"list" | "submit">("list");
  const [page, setPage] = useState(1);
  const [filterStatus, setFilterStatus] = useState<"" | LostPropertyStatus>("");
  const [filterItemType, setFilterItemType] = useState<"" | LostPropertyItemTypes>("");
  const [selectedImage, setSelectedImage] = useState<{ url: string; reportId: number } | null>(null);
  
  const queryClient = useQueryClient();

  // Fetch lost property reports
  const { data: reportsData, isLoading: reportsLoading } = useQuery<any>({
    queryKey: ["lost-property-reports", page, filterStatus, filterItemType],
    queryFn: () =>
      fetchData({
        endpoint: "/api/complaints/passenger/lost-property/",
        token: token,
        queryParams: {
          page: page.toString(),
          page_size: "10",
          ...(filterStatus && { status: filterStatus }),
          ...(filterItemType && { item_type: filterItemType }),
        },
      }),
    enabled: activeTab === "list",
  });

  // Fetch user's completed trips for the dropdown (only completed trips can have lost property reports)
  const { data: tripsData } = useQuery<any>({
    queryKey: ["trips-for-lost-property"],
    queryFn: () =>
      fetchData({
        endpoint: "/api/trips/list-trips/",
        token: token,
        queryParams: {
          page_size: "100",
          trip_status: "completed",
          locale: locale,
        },
      }),
    enabled: activeTab === "submit",
  });

  const reports = reportsData?.data?.lost_property_reports || [];
  const stats = reportsData?.data?.stats || {};
  const pagination = reportsData?.data?.pagination || {};
  const trips = tripsData?.trips || [];

  // Submit lost property report mutation
  const submitMutation = useMutation({
    mutationFn: async (submitData: typeof formData) => {
      const body: any = {
        trip: parseInt(submitData.trip),
        item_type: submitData.item_type,
        item_description: submitData.item_description,
        item_color: submitData.item_color,
        lost_location: submitData.lost_location,
        contact_preference: submitData.contact_preference,
      };
      
      if (submitData.item_brand) {
        body.item_brand = submitData.item_brand;
      }
      
      if (submitData.photo_base64) {
        body.photo_base64 = submitData.photo_base64;
      }
      
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/complaints/passenger/lost-property/submit/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(body),
        }
      );
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to submit report");
      }
      
      return response.json();
    },
    onSuccess: () => {
      toast.success(trans.submit_form.success_message);
      queryClient.invalidateQueries({ queryKey: ["lost-property-reports"] });
      setActiveTab("list");
      // Reset form
      setFormData({
        trip: "",
        item_type: "" as "" | LostPropertyItemTypes,
        item_description: "",
        item_color: "",
        item_brand: "",
        lost_location: "",
        contact_preference: "" as "" | LostPropertyContactPreferences,
        photo: null,
        photo_base64: "",
      });
    },
    onError: (error: any) => {
      const errorMessage = extract_error(error) || error?.message || trans.submit_form.error_message;
      toast.error(errorMessage);
    },
  });

  const statusOptions = Object.values(LostPropertyStatus);
  const itemTypeOptions = Object.values(LostPropertyItemTypes);
  const contactPreferenceOptions = Object.values(LostPropertyContactPreferences);

  const [formData, setFormData] = useState({
    trip: "",
    item_type: "" as "" | LostPropertyItemTypes,
    item_description: "",
    item_color: "",
    item_brand: "",
    lost_location: "",
    contact_preference: "" as "" | LostPropertyContactPreferences,
    photo: null as File | null,
    photo_base64: "" as string,
  });

  const humanize = (value: string) =>
    value
      .replace(/_/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .replace(/\b\w/g, (char) => char.toUpperCase());

  const getItemTypeLabel = (value: string) =>
    trans?.report_list?.item_types?.[value as keyof typeof trans.report_list.item_types] ?? humanize(value);

  const getStatusLabel = (value: string) => {
    if (Array.isArray(trans?.status)) {
      const match = trans.status.find((s: any) => s.value === value);
      if (match?.title) return match.title;
    }
    return trans?.statuses?.[value as keyof typeof trans.statuses] ?? humanize(value);
  };

  const getContactLabel = (value: string) =>
    trans?.submit_form?.fields?.contact_options?.[value as keyof typeof trans.submit_form.fields.contact_options] ??
    trans?.contact_preferences?.[value as keyof typeof trans.contact_preferences] ??
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    if (!formData.trip) {
      toast.error(trans.submit_form.validation.trip_required);
      return;
    }
    if (!formData.item_type) {
      toast.error(trans.submit_form.validation.item_type_required);
      return;
    }
    if (formData.item_type && !itemTypeOptions.includes(formData.item_type)) {
      toast.error(
        trans.submit_form.validation.item_type_invalid || "Please select a valid item type"
      );
      return;
    }
    if (!formData.item_description || formData.item_description.length < 10) {
      toast.error(trans.submit_form.validation.description_min);
      return;
    }
    if (!formData.item_color) {
      toast.error(trans.submit_form.validation.color_required);
      return;
    }
    if (!formData.lost_location) {
      toast.error(trans.submit_form.validation.lost_location_required);
      return;
    }
    if (!formData.contact_preference) {
      toast.error(trans.submit_form.validation.contact_preference_required);
      return;
    }
    if (
      formData.contact_preference &&
      !contactPreferenceOptions.includes(formData.contact_preference)
    ) {
      toast.error(
        trans.submit_form.validation.contact_preference_invalid ||
          "Please select a valid contact preference"
      );
      return;
    }

    submitMutation.mutate(formData);
  };

  const getStatusColor = (status: LostPropertyStatus | string) => {
    switch (status) {
      case LostPropertyStatus.REPORTED:
        return "bg-blue-500/20 text-blue-400 border-blue-500/30";
      case LostPropertyStatus.UNDER_INVESTIGATION:
        return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
      case LostPropertyStatus.FOUND:
        return "bg-green-500/20 text-green-400 border-green-500/30";
      case LostPropertyStatus.RETURNED:
        return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
      case LostPropertyStatus.NOT_FOUND:
        return "bg-red-500/20 text-red-400 border-red-500/30";
      case LostPropertyStatus.CLOSED:
        return "bg-gray-500/20 text-gray-400 border-gray-500/30";
      default:
        return "bg-gray-500/20 text-gray-400 border-gray-500/30";
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
      toast.success(trans.image_downloaded || "Image downloaded successfully");
    } catch (error) {
      toast.error(trans.image_download_failed || "Failed to download image");
    }
  };

  return (
    <div className="w-full">
      {/* Image Preview Modal */}
      {selectedImage && (
        <div
          onClick={() => setSelectedImage(null)}
          className="fixed inset-0 bg-black/80 bg-opacity-80 flex items-center justify-center z-50 p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-foreground rounded-lg p-6 max-w-5xl w-full max-h-[95vh] overflow-auto"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white text-xl font-bold">
                {trans.report_card.photo || "Photo Preview"}
              </h3>
              <button
                onClick={() => setSelectedImage(null)}
                className="text-gray-400 hover:text-white transition-colors p-2 hover:bg-muted/50 rounded-full"
              >
                <FaTimes className="text-2xl" />
              </button>
            </div>
            <div className="relative w-full mb-4 rounded-lg overflow-hidden bg-black/20 flex items-center justify-center min-h-[400px]">
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
      {/* Header with Stats */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="bg-primary/20 p-3 rounded-lg">
            <FaBox className="text-primary text-2xl" />
          </div>
          <div>
            <h1 className="font-bold text-2xl md:text-3xl text-white">
              {trans.title}
            </h1>
            <p className="text-gray-400 text-sm mt-1">{trans.subtitle}</p>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
          {Object.entries(stats).map(([key, value]: [string, any]) => (
            <div
              key={key}
              className="bg-foreground/50 backdrop-blur-sm rounded-lg p-4 border border-muted/10"
            >
              <p className="text-gray-400 text-xs mb-1">{trans.stats[key]}</p>
              <p className="text-white text-xl font-bold">{value}</p>
            </div>
          ))}
        </div>

        {/* Tab Buttons */}
        <div className="bg-foreground/50 backdrop-blur-sm rounded-xl p-2 border border-muted/10">
          <div className="flex items-center justify-start gap-2">
            <button
              onClick={() => setActiveTab("list")}
              className={`
                px-4 py-2.5 rounded-lg text-sm md:text-base font-semibold
                transition-all duration-300 ease-in-out flex items-center gap-2
                ${
                  activeTab === "list"
                    ? "bg-primary text-black shadow-lg shadow-primary/30"
                    : "bg-transparent text-gray-300 hover:bg-muted/20 hover:text-white"
                }
              `}
            >
              <FaList />
              {trans.tabs.my_reports}
            </button>
            <button
              onClick={() => setActiveTab("submit")}
              className={`
                px-4 py-2.5 rounded-lg text-sm md:text-base font-semibold
                transition-all duration-300 ease-in-out flex items-center gap-2
                ${
                  activeTab === "submit"
                    ? "bg-primary text-black shadow-lg shadow-primary/30"
                    : "bg-transparent text-gray-300 hover:bg-muted/20 hover:text-white"
                }
              `}
            >
              <FaPlus />
              {trans.tabs.submit_report}
            </button>
          </div>
        </div>
      </div>

      {/* Content Area */}
      {activeTab === "list" ? (
        <div>
          {/* Filters */}
          <div className="bg-foreground/50 backdrop-blur-sm rounded-xl p-4 mb-6 border border-muted/10">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Status Filter */}
              <div>
                <label className="block mb-2 text-[16px] text-gray-300">
                  {trans.report_list.filter.status_label}
                </label>
                <select
                  value={filterStatus}
                  onChange={(e) => {
                    setFilterStatus(e.target.value as "" | LostPropertyStatus);
                    setPage(1);
                  }}
                  className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary"
                >
                  <option value="" className="bg-foreground text-gray-400">{trans.report_list.filter.all}</option>
                  {statusOptions.map((status) => (
                    <option key={status} value={status} className="bg-foreground text-white">
                      {getStatusLabel(status)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Item Type Filter */}
              <div>
                <label className="block mb-2 text-[16px] text-gray-300">
                  {trans.report_list.filter.item_type_label}
                </label>
                <select
                  value={filterItemType}
                  onChange={(e) => {
                    setFilterItemType(e.target.value as "" | LostPropertyItemTypes);
                    setPage(1);
                  }}
                  className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary"
                >
                  <option value="" className="bg-foreground text-gray-400">{trans.report_list.item_types.all}</option>
                  {itemTypeOptions.map((type) => (
                    <option key={type} value={type} className="bg-foreground text-white">
                      {getItemTypeLabel(type)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Reports List */}
          {reportsLoading ? (
            <div className="flex items-center justify-center py-20">
              <IsLoading />
            </div>
          ) : reports.length === 0 ? (
            <div className="bg-foreground/30 backdrop-blur-sm rounded-xl p-12 border border-muted/10 text-center">
              <FaBox className="text-gray-500 text-5xl mx-auto mb-4" />
              <p className="text-gray-400 text-lg">{trans.report_list.empty}</p>
            </div>
          ) : (
            <div className="space-y-4">
              {reports.map((report: any) => (
                <div
                  key={report.id}
                  className="bg-foreground/50 backdrop-blur-sm rounded-xl p-6 border border-muted/10 hover:border-primary/30 transition-all duration-300"
                >
                  <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <span
                          className={`px-3 py-1 rounded-lg text-xs font-semibold border ${getStatusColor(
                            report.status
                          )}`}
                        >
                          {getStatusLabel(report.status) || report.status_display}
                        </span>
                        <span className="text-gray-400 text-sm">
                          {trans.report_card.report_id}: #{report.id}
                        </span>
                      </div>
                      
                      <h3 className="text-white text-lg font-bold mb-2">
                        {getItemTypeLabel(report.item_type) ||
                          report.item_type_display}
                      </h3>
                      
                      <p className="text-gray-300 mb-3">{report.item_description}</p>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                        {report.item_color && (
                          <div>
                            <span className="text-gray-400">
                              {trans.report_card.color}:{" "}
                            </span>
                            <span className="text-white">{report.item_color}</span>
                          </div>
                        )}
                      {report.item_brand && (
                        <div>
                          <span className="text-gray-400">
                            {trans.report_card.brand}:{" "}
                          </span>
                          <span className="text-white">{report.item_brand}</span>
                        </div>
                      )}
                      <div>
                        <span className="text-gray-400">
                          {trans.report_card.lost_location}:{" "}
                        </span>
                        <span className="text-white">{report.lost_location}</span>
                      </div>
                      <div>
                        <span className="text-gray-400">
                          {trans.report_card.contact_preference}:{" "}
                        </span>
                        <span className="text-white">
                          {getContactLabel(report.contact_preference) ||
                            report.contact_preference_display}
                        </span>
                      </div>
                    </div>
                    
                    {/* Photo Display */}
                    {report.photo && (
                      <div className="mt-4">
                        <p className="text-gray-400 text-sm mb-2">
                          {trans.report_card.photo || "Photo"}
                        </p>
                        <div 
                          className="relative w-full max-w-xs h-48 rounded-lg overflow-hidden border-2 border-muted/20 cursor-pointer hover:border-primary/50 transition-all duration-300"
                          onClick={() => setSelectedImage({ url: getPhotoUrl(report.photo), reportId: report.id })}
                        >
                          <img
                            src={getPhotoUrl(report.photo)}
                            alt="Lost item photo"
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              // Fallback if image fails to load
                              (e.target as HTMLImageElement).style.display = 'none';
                            }}
                          />
                          <div className="absolute inset-0 bg-black/0 hover:bg-black/10 transition-all duration-300 flex items-center justify-center">
                            <span className="text-white opacity-0 hover:opacity-100 text-sm font-semibold">{trans.click_to_view || "Click to view"}</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                    <div className="text-sm text-gray-400 md:text-right">
                      {report.trip_data && (
                        <div className="mb-2">
                          <span className="block font-semibold text-white mb-1">
                            {trans.report_card.trip_date}
                          </span>
                          <span>{report.trip_data.trip_date}</span>
                        </div>
                      )}
                      <div>
                        <span className="block font-semibold text-white mb-1">
                          {trans.report_card.created_at}
                        </span>
                        <span>
                          {new Date(report.created_at).toLocaleDateString(
                            locale === "ar" ? "ar-EG" : "en-US"
                          )}
                        </span>
                      </div>
                    </div>
                  </div>

                  {report.admin_notes && (
                    <div className="mt-4 p-4 bg-primary/10 border border-primary/20 rounded-lg">
                      <p className="text-gray-400 text-sm mb-1">
                        {trans.report_card.admin_notes}:
                      </p>
                      <p className="text-white">{report.admin_notes}</p>
                    </div>
                  )}

                  {report.found_at && (
                    <div className="mt-2 text-sm">
                      <span className="text-gray-400">
                        {trans.report_card.found_at}:{" "}
                      </span>
                      <span className="text-green-400">
                        {new Date(report.found_at).toLocaleDateString(
                          locale === "ar" ? "ar-EG" : "en-US"
                        )}
                      </span>
                    </div>
                  )}

                  {report.returned_at && (
                    <div className="mt-2 text-sm">
                      <span className="text-gray-400">
                        {trans.report_card.returned_at}:{" "}
                      </span>
                      <span className="text-emerald-400">
                        {new Date(report.returned_at).toLocaleDateString(
                          locale === "ar" ? "ar-EG" : "en-US"
                        )}
                      </span>
                    </div>
                  )}
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
        </div>
      ) : (
        /* Submit Form */
        <div className="bg-foreground/50 backdrop-blur-sm rounded-xl p-6 md:p-8 border border-muted/10">
          <h2 className="text-white text-xl font-bold mb-2">
            {trans.submit_form.title}
          </h2>
          <p className="text-gray-400 mb-6">{trans.submit_form.subtitle}</p>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Two Column Layout */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Trip Selection */}
              <div>
                <label className="block mb-2 text-[16px] text-gray-300">
                  {trans.submit_form.fields.trip} <span className="text-primary">*</span>
                </label>
                <select
                  value={formData.trip}
                  onChange={(e) => setFormData({ ...formData, trip: e.target.value })}
                  className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary"
                  required
                >
                  <option value="" className="bg-foreground text-gray-400">
                    {trans.submit_form.fields.trip_placeholder}
                  </option>
                  {trips.map((trip: any) => (
                    <option key={trip.id} value={trip.id} className="bg-foreground text-white">
                      Trip #{trip.id} - {trip.trip_date} {trip.trip_time}
                    </option>
                  ))}
                </select>
              </div>

              {/* Item Type */}
              <div>
                <label className="block mb-2 text-[16px] text-gray-300">
                  {trans.submit_form.fields.item_type} <span className="text-primary">*</span>
                </label>
                <select
                  value={formData.item_type}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      item_type: e.target.value as "" | LostPropertyItemTypes,
                    })
                  }
                  className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary"
                  required
                >
                  <option value="" className="bg-foreground text-gray-400">{trans.select_item_type || "Select item type"}</option>
                  {itemTypeOptions.map((type) => (
                    <option key={type} value={type} className="bg-foreground text-white">
                      {getItemTypeLabel(type)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Item Color */}
              <div>
                <label className="block mb-2 text-[16px] text-gray-300">
                  {trans.submit_form.fields.item_color} <span className="text-primary">*</span>
                </label>
                <input
                  type="text"
                  value={formData.item_color}
                  onChange={(e) =>
                    setFormData({ ...formData, item_color: e.target.value })
                  }
                  placeholder={trans.submit_form.fields.item_color_placeholder}
                  className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary placeholder:text-gray-400"
                  required
                />
              </div>

              {/* Item Brand (Optional) */}
              <div>
                <label className="block mb-2 text-[16px] text-gray-300">
                  {trans.submit_form.fields.item_brand}
                </label>
                <input
                  type="text"
                  value={formData.item_brand}
                  onChange={(e) =>
                    setFormData({ ...formData, item_brand: e.target.value })
                  }
                  placeholder={trans.submit_form.fields.item_brand_placeholder}
                  className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary placeholder:text-gray-400"
                />
              </div>

              {/* Lost Location */}
              <div>
                <label className="block mb-2 text-[16px] text-gray-300">
                  {trans.submit_form.fields.lost_location} <span className="text-primary">*</span>
                </label>
                <select
                  value={formData.lost_location}
                  onChange={(e) =>
                    setFormData({ ...formData, lost_location: e.target.value })
                  }
                  className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary"
                  required
                >
                  <option value="" className="bg-foreground text-gray-400">
                    {trans.submit_form.fields.lost_location_placeholder}
                  </option>
                  {Object.keys(trans.lost_locations).map((location) => (
                    <option key={location} value={trans.lost_locations[location]} className="bg-foreground text-white">
                      {trans.lost_locations[location]}
                    </option>
                  ))}
                </select>
              </div>

              {/* Contact Preference */}
              <div>
                <label className="block mb-2 text-[16px] text-gray-300">
                  {trans.submit_form.fields.contact_preference} <span className="text-primary">*</span>
                </label>
                <select
                  value={formData.contact_preference}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      contact_preference: e.target.value as
                        | ""
                        | LostPropertyContactPreferences,
                    })
                  }
                  className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary"
                  required
                >
                  <option value="" className="bg-foreground text-gray-400">{trans.select_contact_method || "Select contact method"}</option>
                  {contactPreferenceOptions.map((option) => (
                    <option key={option} value={option} className="bg-foreground text-white">
                      {getContactLabel(option)}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Item Description - Full Width */}
            <div>
              <label className="block mb-2 text-[16px] text-gray-300">
                {trans.submit_form.fields.item_description} <span className="text-primary">*</span>
              </label>
              <textarea
                value={formData.item_description}
                onChange={(e) =>
                  setFormData({ ...formData, item_description: e.target.value })
                }
                placeholder={trans.submit_form.fields.item_description_placeholder}
                className="w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg focus:outline-none focus:border-primary min-h-[120px] placeholder:text-gray-400"
                required
              />
            </div>

            {/* Photo Upload - Full Width */}
            <div>
              <label className="block mb-2 text-[16px] text-gray-300">
                {trans.submit_form.fields.photo || "Photo (Optional)"}
              </label>
              <div className="flex flex-col gap-3">
                <label 
                  htmlFor="photo-upload"
                  className="flex items-center gap-3 p-3 border-2 bg-foreground text-white border-muted rounded-lg focus-within:border-primary cursor-pointer hover:border-primary/50 transition-colors"
                >
                  <span className="text-primary font-semibold">{trans.choose_file || "Choose File"}</span>
                  <span className="text-gray-400 text-sm">
                    {formData.photo ? formData.photo.name : trans.no_file_chosen || "No file chosen"}
                  </span>
                </label>
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  id="photo-upload"
                  onChange={(e) => {
                    const file = e.target.files?.[0] || null;
                    if (file) {
                      // Convert file to base64
                      const reader = new FileReader();
                      reader.onloadend = () => {
                        const base64String = reader.result as string;
                        setFormData({ 
                          ...formData, 
                          photo: file,
                          photo_base64: base64String 
                        });
                      };
                      reader.onerror = () => {
                        toast.error(trans.file_read_failed || "Failed to read image file");
                      };
                      reader.readAsDataURL(file);
                    } else {
                      setFormData({ 
                        ...formData, 
                        photo: null,
                        photo_base64: "" 
                      });
                    }
                  }}
                />
                {formData.photo && formData.photo_base64 && (
                  <div className="mt-2">
                    <p className="text-sm text-gray-400 mb-2">
                      {trans.submit_form.fields.selected_photo || "Selected:"} {formData.photo.name}
                    </p>
                    <div className="relative w-full max-w-xs h-48 rounded-lg overflow-hidden border-2 border-muted">
                      <img
                        src={formData.photo_base64}
                        alt="Preview"
                        className="w-full h-full object-cover"
                      />
                    </div>
                  </div>
                )}
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {trans.submit_form.fields.photo_description || "Upload a photo of the lost item if available"}
              </p>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitMutation.isPending}
              className="w-full bg-primary hover:bg-primary/90 text-black font-bold py-3 px-6 rounded-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitMutation.isPending
                ? trans.submit_form.button_loading
                : trans.submit_form.button}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

