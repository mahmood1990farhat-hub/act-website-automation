"use client";

import React, { useState, useMemo } from "react";
import { useForm, SubmitHandler } from "react-hook-form";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Locale } from "../../../../i18n.config";
import { fetchData } from "@/lib/api/fetchData";
import { postData } from "@/lib/api/postData";
import { putData } from "@/lib/api/putApi";
import { deleteData } from "@/lib/api/deleteApi";
import { toast } from "react-toastify";
import { Button } from "@/components/ui/button";
import IsLoading from "../ISloading";
import GlobalModal from "../GlobalModal";
import { extract_error } from "@/lib/api/errorApi";
import { FaEdit, FaTrash, FaPlus, FaCheckCircle, FaTimesCircle } from "react-icons/fa";
import Pagination from "../Pagination";
import { VEHICLE_TYPES } from "@/lib/constants/vehicleTypes";
import CustomSelectInput from "../ControlledFields/CustomSelectInput";

type PeakTimeRule = {
  id: number;
  name: string;
  is_active: boolean;
  start_time: string;
  end_time: string;
  days_of_week: number[];
  multiplier: string;
  vehicle_type: {
    id: number;
    name_en: string;
    name_ar: string;
  };
  priority: number;
};

type VehicleType = {
  id: number;
  name_en: string;
  name_ar: string;
};

type PeakTimeRulesResponse = {
  success: boolean;
  message: string;
  data: PeakTimeRule[];
  pagination: {
    count: number;
    num_pages: number;
    current_page: number;
    page_size: number;
  };
};

type VehicleTypesResponse = {
  success: boolean;
  data: VehicleType[];
};

type PeakTimeRuleFormData = {
  name: string;
  is_active: boolean;
  start_time: string;
  end_time: string;
  days_of_week: number[];
  multiplier: string;
  vehicle_type_ids: number [] | string[];
  priority: number;
};

type PeakTimeRulesProps = {
  trans: any;
  token?: string;
  locale: Locale;
};

const DAYS_OF_WEEK = [
  { value: 0, label: "Monday" },
  { value: 1, label: "Tuesday" },
  { value: 2, label: "Wednesday" },
  { value: 3, label: "Thursday" },
  { value: 4, label: "Friday" },
  { value: 5, label: "Saturday" },
  { value: 6, label: "Sunday" },
];

const DAYS_OF_WEEK_AR = [
  { value: 0, label: "الاثنين" },
  { value: 1, label: "الثلاثاء" },
  { value: 2, label: "الأربعاء" },
  { value: 3, label: "الخميس" },
  { value: 4, label: "الجمعة" },
  { value: 5, label: "السبت" },
  { value: 6, label: "الأحد" },
];

export default function PeakTimeRules({
  trans,
  token,
  locale,
}: PeakTimeRulesProps) {
  const [page, setPage] = useState(1);
  const [showFormModal, setShowFormModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedRule, setSelectedRule] = useState<PeakTimeRule | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const queryClient = useQueryClient();

  const daysOptions = locale === "ar" ? DAYS_OF_WEEK_AR : DAYS_OF_WEEK;

  // Fetch peak time rules
  const {
    data: rulesData,
    isLoading,
    error,
  } = useQuery<PeakTimeRulesResponse>({
    queryKey: ["peak-time-rules", page, token, locale],
    queryFn: async () => {
      try {
        return await fetchData({
          endpoint: "/api/pricing/peak-rules/",
          token,
          queryParams: {
            locale,
            page: page.toString(),
            page_size: "10",
          },
        });
      } catch (err: any) {
        console.error("Failed to fetch peak time rules:", err);
        toast.error(
          extract_error(err) || err?.message || "Failed to load peak time rules"
        );
        throw err;
      }
    },
    enabled: !!token,
    retry: 1,
    refetchOnWindowFocus: false,
  });


  const {
    register,
    handleSubmit,
    reset,
    control,
    watch,
    formState: { errors },
  } = useForm<PeakTimeRuleFormData>({
    defaultValues: {
      name: "",
      is_active: true,
      start_time: "10:00",
      end_time: "18:00",
      days_of_week: [],
      multiplier: "1.000",
      vehicle_type_ids: [],
      priority: 1,
    },
  });

  const selectedDays = watch("days_of_week") || [];

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: PeakTimeRuleFormData) =>
      postData({
        endpoint: "/api/pricing/peak-rules/",
        token,
        body: {
          ...data,
          start_time: `${data.start_time}:00`,
          end_time: `${data.end_time}:00`,
        },
        queryParams: { locale },
        noToast: false, // Let API show toast
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["peak-time-rules"] });
      setShowFormModal(false);
      reset();
      setSelectedRule(null);
      setIsEditing(false);
    },
    onError: () => {
      // Error toast is handled by postData
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: PeakTimeRuleFormData }) =>
      putData({
        endpoint: `/api/pricing/peak-rules/${id}/`,
        token,
        body: {
          ...data,
          start_time: `${data.start_time}:00`,
          end_time: `${data.end_time}:00`,
        },
        queryParams: { locale },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["peak-time-rules"] });
      toast.success(trans.peakTime?.updateSuccess || "Peak time rule updated successfully");
      setShowFormModal(false);
      reset();
      setSelectedRule(null);
      setIsEditing(false);
    },
    onError: (error: any) => {
      const errorMessage =
        extract_error(error) || error?.message || "Failed to update peak time rule";
      toast.error(errorMessage);
    },
  });

  const { data: vehicleTypes =[] ,isLoading :isLoadingVehicleTypes } =
    useQuery({
      queryKey: ["vehicle-types"],
      queryFn: async () =>
        fetchData<{ name_ar: string; name_en: string; id: number }[]>({ endpoint: "/api/vehicle/vehicle-types/" }),
      select: (data) =>
        data.map((item) => ({
          label: item.name_en,
          value: item.id.toString(),
        })),
    }) || [];
  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      deleteData({
        endpoint: `/api/pricing/peak-rules/${id}`,
        token,
        queryParams: { locale },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["peak-time-rules"] });
      toast.success(trans.peakTime?.deleteSuccess || "Peak time rule deleted successfully");
      setShowDeleteModal(false);
      setSelectedRule(null);
    },
    onError: (error: any) => {
      const errorMessage =
        extract_error(error) || error?.message || "Failed to delete peak time rule";
      toast.error(errorMessage);
    },
  });

  const handleCreate = () => {
    setIsEditing(false);
    setSelectedRule(null);
    reset({
      name: "",
      is_active: true,
      start_time: "10:00",
      end_time: "18:00",
      days_of_week: [],
      multiplier: "1.000",
      vehicle_type_ids: [],
      priority: 1,
    });
    setShowFormModal(true);
  };

  const handleEdit = (rule: PeakTimeRule) => {
    setIsEditing(true);
    setSelectedRule(rule);
    // Extract time from "HH:MM:SS" format
    const startTime = rule.start_time.substring(0, 5);
    const endTime = rule.end_time.substring(0, 5);
    reset({
      name: rule.name,
      is_active: rule.is_active,
      start_time: startTime,
      end_time: endTime,
      days_of_week: rule.days_of_week,
      multiplier: rule.multiplier,
      vehicle_type_ids: [rule.vehicle_type.id.toString()],
      priority: rule.priority,
    });
    setShowFormModal(true);
  };

  const handleDelete = (rule: PeakTimeRule) => {
    setSelectedRule(rule);
    setShowDeleteModal(true);
  };

  const onSubmit: SubmitHandler<PeakTimeRuleFormData> = (data) => {
    // Ensure days_of_week is an array
    const submitData = {
      ...data,
      days_of_week: Array.isArray(data.days_of_week) ? data.days_of_week : [],
    };
    
    if (submitData.days_of_week.length === 0) {
      toast.error(trans.peakTime?.daysRequired || "Please select at least one day");
      return;
    }

    if (isEditing && selectedRule) {
      updateMutation.mutate({ id: selectedRule.id, data: submitData });
    } else {
      createMutation.mutate(submitData);
    }
  };

  const handleDeleteConfirm = () => {
    if (selectedRule) {
      deleteMutation.mutate(selectedRule.id);
    }
  };

  const toggleDay = (day: number) => {
    const currentDays = selectedDays || [];
    const newDays = currentDays.includes(day)
      ? currentDays.filter((d) => d !== day)
      : [...currentDays, day];
    reset({ ...watch(), days_of_week: newDays }, { keepDirty: true });
  };

  const rules = rulesData?.data || [];
  const pagination = rulesData?.pagination || {
    count: 0,
    num_pages: 1,
    current_page: 1,
    page_size: 10,
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <IsLoading />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4">
        <p className="text-red-700 font-medium">
          {trans.peakTime?.loadError ||
            "Failed to load peak time rules. Please try again."}
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Header with Add Button */}
      <div className="flex items-center justify-between mb-4">
        <Button
          onClick={handleCreate}
          className="w-full sm:w-auto bg-primary hover:bg-primary/90 text-foreground font-semibold shadow-lg shadow-primary/30 text-sm md:text-base"
        >
          <FaPlus className="mr-2" />
          {trans.peakTime?.addButton || "Add Peak Time Rule"}
        </Button>
      </div>

      {rules.length === 0 ? (
        <div className="bg-card rounded-xl shadow-xl border-2 border-border p-8 md:p-12 text-center">
          <p className="text-muted-foreground text-base md:text-lg">
            {trans.peakTime?.empty || "No peak time rules found"}
          </p>
        </div>
      ) : (
        <>
          {/* Desktop Table */}
          <div className="hidden xl:block">
            <div className="bg-card rounded-xl shadow-xl border-2 border-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[900px] text-xs md:text-sm">
              <thead>
                <tr className="border-b-2 border-border bg-gray-100 dark:bg-gray-800">
                  <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.peakTime?.name || "Name"}
                  </th>
                  <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.peakTime?.vehicleType || "Vehicle Type"}
                  </th>
                  <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.peakTime?.days || "Days"}
                  </th>
                  <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.peakTime?.time || "Time"}
                  </th>
                  <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.peakTime?.multiplier || "Multiplier"}
                  </th>
                  <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.peakTime?.priority || "Priority"}
                  </th>
                  <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.peakTime?.status || "Status"}
                  </th>
                  <th className="text-center py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.peakTime?.actions || "Actions"}
                  </th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr
                    key={rule.id}
                    className="border-b border-border hover:bg-muted transition-colors"
                  >
                    <td className="py-3 px-4 font-bold text-foreground">
                      {rule.name}
                    </td>
                    <td className="py-3 px-4 text-foreground">
                      {locale === "ar"
                        ? rule.vehicle_type.name_ar
                        : rule.vehicle_type.name_en}
                    </td>
                    <td className="py-3 px-4 text-foreground">
                      <div className="flex flex-wrap gap-1">
                        {rule.days_of_week
                          .sort((a, b) => a - b)
                          .map((day) => (
                            <span
                              key={day}
                              className="px-2 py-0.5 bg-primary/10 text-primary rounded text-xs font-medium"
                            >
                              {daysOptions.find((d) => d.value === day)?.label}
                            </span>
                          ))}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-foreground">
                      {rule.start_time.substring(0, 5)} - {rule.end_time.substring(0, 5)}
                    </td>
                    <td className="py-3 px-4 text-foreground font-semibold">
                      {rule.multiplier}x
                    </td>
                    <td className="py-3 px-4 text-foreground">{rule.priority}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full font-bold ${
                          rule.is_active
                            ? "bg-green-50 text-green-700 border border-green-200"
                            : "bg-red-50 text-red-700 border border-red-200"
                        }`}
                      >
                        {rule.is_active ? (
                          <>
                            <FaCheckCircle className="mr-1" />
                            {trans.peakTime?.active || "Active"}
                          </>
                        ) : (
                          <>
                            <FaTimesCircle className="mr-1" />
                            {trans.peakTime?.inactive || "Inactive"}
                          </>
                        )}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          onClick={() => handleEdit(rule)}
                          variant="ghost"
                          className="p-1.5 hover:bg-muted text-yellow-600 hover:text-yellow-700 transition-colors"
                          title={trans.peakTime?.edit || "Edit"}
                        >
                          <FaEdit className="text-base" />
                        </Button>
                        <Button
                          onClick={() => handleDelete(rule)}
                          variant="ghost"
                          className="p-1.5 hover:bg-muted text-red-600 hover:text-red-700 transition-colors"
                          title={trans.peakTime?.delete || "Delete"}
                        >
                          <FaTrash className="text-base" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
                </table>
              </div>
              {pagination.num_pages > 1 && (
                <div className="flex items-center justify-between px-4 md:px-6 py-4 border-t-2 border-border">
                  <div className="text-xs md:text-sm text-muted-foreground">
                    {trans.pagination?.table || "Page"} {page} {trans.pagination?.of || "of"}{" "}
                    {pagination.num_pages} {trans.pagination?.tables || "pages"}
                  </div>
                  <Pagination
                    currentPage={page}
                    onPageChange={setPage}
                    locale={locale}
                    totalPages={pagination.num_pages}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Mobile Cards */}
          <div className="xl:hidden space-y-4">
            {rules.map((rule) => (
              <div
                key={rule.id}
                className="bg-card rounded-xl shadow-lg border-2 border-border p-4 hover:shadow-xl hover:border-primary/60 transition-all"
              >
                <div className="flex items-start justify-between mb-3 pb-3 border-b-2 border-border">
                  <div className="flex-1">
                    <h3 className="font-bold text-base md:text-lg text-foreground mb-1">
                      {rule.name}
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      {locale === "ar"
                        ? rule.vehicle_type.name_ar
                        : rule.vehicle_type.name_en}
                    </p>
                  </div>
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                      rule.is_active
                        ? "bg-green-50 text-green-700 border-green-200"
                        : "bg-red-50 text-red-700 border-red-200"
                    }`}
                  >
                    {rule.is_active ? (
                      <>
                        <FaCheckCircle className="mr-1" />
                        {trans.peakTime?.active || "Active"}
                      </>
                    ) : (
                      <>
                        <FaTimesCircle className="mr-1" />
                        {trans.peakTime?.inactive || "Inactive"}
                      </>
                    )}
                  </span>
                </div>
                <div className="space-y-2 mb-3">
                  <div className="flex flex-wrap gap-1">
                    {rule.days_of_week
                      .sort((a, b) => a - b)
                      .map((day) => (
                        <span
                          key={day}
                          className="px-2 py-0.5 bg-primary/10 text-primary rounded text-xs font-medium"
                        >
                          {daysOptions.find((d) => d.value === day)?.label}
                        </span>
                      ))}
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-muted/50 p-2 rounded-lg">
                      <p className="text-xs text-muted-foreground mb-1">
                        {trans.peakTime?.time || "Time"}
                      </p>
                      <p className="font-semibold text-sm text-foreground">
                        {rule.start_time.substring(0, 5)} - {rule.end_time.substring(0, 5)}
                      </p>
                    </div>
                    <div className="bg-muted/50 p-2 rounded-lg">
                      <p className="text-xs text-muted-foreground mb-1">
                        {trans.peakTime?.multiplier || "Multiplier"}
                      </p>
                      <p className="font-semibold text-sm text-foreground">
                        {rule.multiplier}x
                      </p>
                    </div>
                    <div className="bg-muted/50 p-2 rounded-lg">
                      <p className="text-xs text-muted-foreground mb-1">
                        {trans.peakTime?.priority || "Priority"}
                      </p>
                      <p className="font-semibold text-sm text-foreground">
                        {rule.priority}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                  <Button
                    onClick={() => handleEdit(rule)}
                    variant="ghost"
                    className="p-2 hover:bg-muted text-yellow-600 hover:text-yellow-700 transition-colors"
                    title={trans.peakTime?.edit || "Edit"}
                  >
                    <FaEdit className="text-base" />
                  </Button>
                  <Button
                    onClick={() => handleDelete(rule)}
                    variant="ghost"
                    className="p-2 hover:bg-muted text-red-600 hover:text-red-700 transition-colors"
                    title={trans.peakTime?.delete || "Delete"}
                  >
                    <FaTrash className="text-base" />
                  </Button>
                </div>
              </div>
            ))}
            {pagination.num_pages > 1 && (
              <div className="flex flex-col items-center gap-3 pt-4">
                <div className="text-xs text-muted-foreground">
                  {trans.pagination?.table || "Page"} {page} {trans.pagination?.of || "of"}{" "}
                  {pagination.num_pages} {trans.pagination?.tables || "pages"}
                </div>
                <Pagination
                  currentPage={page}
                  onPageChange={setPage}
                  locale={locale}
                  totalPages={pagination.num_pages}
                />
              </div>
            )}
          </div>
        </>
      )}

      {/* Create/Edit Modal */}
      <GlobalModal
        isOpen={showFormModal}
        onClose={() => {
          if (!createMutation.isPending && !updateMutation.isPending) {
            setShowFormModal(false);
            reset();
            setSelectedRule(null);
            setIsEditing(false);
          }
        }}
      >
        <div className="p-4 md:p-6 w-full">
          <h2 className="text-lg md:text-xl font-bold text-foreground mb-4 md:mb-6">
            {isEditing
              ? trans.peakTime?.editTitle || "Edit Peak Time Rule"
              : trans.peakTime?.createTitle || "Create New Peak Time Rule"}
          </h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
              {/* Name */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-foreground mb-2">
                  {trans.peakTime?.name || "Name"}
                  <span className="text-red-500 ml-1">*</span>
                </label>
                <input
                  type="text"
                  {...register("name", {
                    required: trans.peakTime?.nameRequired || "Name is required",
                  })}
                  placeholder={trans.peakTime?.namePlaceholder || "Weekend Peak"}
                  className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
                />
                {errors.name && (
                  <p className="text-error text-sm mt-1">{errors.name.message}</p>
                )}
              </div>

              {/* Vehicle Type */}
              <div>
                    <CustomSelectInput  
                                  name="vehicle_type_ids"
                                  label=               {trans.peakTime?.vehicleType || "Vehicle Type"}
                                  control={control}
                                  options={vehicleTypes || []}
                                  isLoading={isLoadingVehicleTypes}
                                  required
                                  containerClassName="col-span-1 md:col-span-2"
                                  isMulti
                                />
             
                {errors.vehicle_type_ids && (
                  <p className="text-error text-sm mt-1">
                    {errors.vehicle_type_ids.message}
                  </p>
                )}
              </div>

              {/* Priority */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {trans.peakTime?.priority || "Priority"}
                  <span className="text-red-500 ml-1">*</span>
                </label>
                <input
                  type="number"
                  {...register("priority", {
                    required: trans.peakTime?.priorityRequired || "Priority is required",
                    valueAsNumber: true,
                    min: { value: 1, message: trans.peakTime?.priorityMin || "Priority must be 1 or greater" },
                  })}
                  className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
                />
                {errors.priority && (
                  <p className="text-error text-sm mt-1">{errors.priority.message}</p>
                )}
              </div>

              {/* Start Time */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {trans.peakTime?.startTime || "Start Time"}
                  <span className="text-red-500 ml-1">*</span>
                </label>
                <input
                  type="time"
                  {...register("start_time", {
                    required: trans.peakTime?.startTimeRequired || "Start time is required",
                  })}
                  className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
                />
                {errors.start_time && (
                  <p className="text-error text-sm mt-1">
                    {errors.start_time.message}
                  </p>
                )}
              </div>

              {/* End Time */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {trans.peakTime?.endTime || "End Time"}
                  <span className="text-red-500 ml-1">*</span>
                </label>
                <input
                  type="time"
                  {...register("end_time", {
                    required: trans.peakTime?.endTimeRequired || "End time is required",
                  })}
                  className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
                />
                {errors.end_time && (
                  <p className="text-error text-sm mt-1">{errors.end_time.message}</p>
                )}
              </div>

              {/* Multiplier */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {trans.peakTime?.multiplier || "Multiplier"}
                  <span className="text-red-500 ml-1">*</span>
                </label>
                <input
                  type="text"
                  {...register("multiplier", {
                    required: trans.peakTime?.multiplierRequired || "Multiplier is required",
                    pattern: {
                      value: /^\d+(\.\d{1,3})?$/,
                      message: trans.peakTime?.multiplierInvalid || "Invalid multiplier format",
                    },
                  })}
                  placeholder="1.150"
                  className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
                />
                {errors.multiplier && (
                  <p className="text-error text-sm mt-1">
                    {errors.multiplier.message}
                  </p>
                )}
              </div>

              {/* Is Active */}
              <div className="flex items-center">
                <label className="flex items-center cursor-pointer group">
                  <input
                    type="checkbox"
                    {...register("is_active")}
                    className="w-5 h-5 text-primary bg-background border-2 border-border rounded focus:ring-2 focus:ring-primary focus:ring-offset-2 cursor-pointer transition-colors"
                  />
                  <span className="ml-3 text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                    {trans.peakTime?.isActive || "Is Active"}
                  </span>
                </label>
              </div>
            </div>

            {/* Days of Week */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-foreground mb-2">
                {trans.peakTime?.daysOfWeek || "Days of Week"}
                <span className="text-red-500 ml-1">*</span>
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                {daysOptions.map((day) => (
                  <label
                    key={day.value}
                    className="flex items-center cursor-pointer p-3 border-2 border-border rounded-lg hover:border-primary transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedDays.includes(day.value)}
                      onChange={() => toggleDay(day.value)}
                      className="w-4 h-4 text-primary bg-background border-border rounded focus:ring-2 focus:ring-primary"
                    />
                    <span className="ml-2 text-sm text-foreground">{day.label}</span>
                  </label>
                ))}
              </div>
              {selectedDays.length === 0 && (
                <p className="text-error text-sm mt-1">
                  {trans.peakTime?.daysRequired || "Please select at least one day"}
                </p>
              )}
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-4 border-t-2 border-border">
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setShowFormModal(false);
                  reset();
                  setSelectedRule(null);
                  setIsEditing(false);
                }}
                disabled={createMutation.isPending || updateMutation.isPending}
                className="w-full sm:flex-1 font-semibold"
              >
                {trans.peakTime?.cancel || "Cancel"}
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="w-full sm:flex-1 font-semibold bg-primary hover:bg-primary/90 text-foreground shadow-lg shadow-primary/30"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? trans.peakTime?.saving || "Saving..."
                  : isEditing
                  ? trans.peakTime?.updateButton || "Update"
                  : trans.peakTime?.createButton || "Create"}
              </Button>
            </div>
          </form>
        </div>
      </GlobalModal>

      {/* Delete Confirmation Modal */}
      <GlobalModal
        isOpen={showDeleteModal}
        onClose={() => {
          if (!deleteMutation.isPending) {
            setShowDeleteModal(false);
            setSelectedRule(null);
          }
        }}
      >
        <div className="p-4 md:p-6 w-full">
          <h2 className="text-lg md:text-xl font-bold text-foreground mb-4">
            {trans.peakTime?.deleteTitle || "Delete Peak Time Rule"}
          </h2>
          <p className="text-sm text-muted-foreground mb-4">
            {trans.peakTime?.deleteMessage ||
              "Are you sure you want to delete this peak time rule? This action cannot be undone."}
          </p>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setShowDeleteModal(false);
                setSelectedRule(null);
              }}
              disabled={deleteMutation.isPending}
              className="w-full sm:flex-1 font-semibold"
            >
              {trans.peakTime?.cancel || "Cancel"}
            </Button>
            <Button
              type="button"
              onClick={handleDeleteConfirm}
              disabled={deleteMutation.isPending}
              className="w-full sm:flex-1 font-semibold bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30 disabled:opacity-60"
            >
              {deleteMutation.isPending
                ? trans.peakTime?.deleting || "Deleting..."
                : trans.peakTime?.deleteConfirm || "Delete"}
            </Button>
          </div>
        </div>
      </GlobalModal>
    </div>
  );
}
